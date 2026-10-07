import streamlit as st
import sqlite3
import random
import string


# PAGE CONFIGURATION

st.set_page_config(
    page_title="Secret Santa 2026",
    page_icon="🎄",
    layout="centered"
)


# DATABASE

DB_NAME = "secret_santa.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


def create_table():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            code TEXT UNIQUE NOT NULL,
            recipient TEXT NOT NULL,
            revealed INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()


create_table()


# ORGANIZER PASSWORD

ORGANIZER_PASSWORD = st.secrets["ORGANIZER_PASSWORD"]


# GENERATE UNIQUE CODE

def generate_code():

    characters = string.ascii_uppercase + string.digits

    while True:

        code = "".join(
            random.choices(characters, k=6)
        )

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id FROM participants WHERE code = ?",
            (code,)
        )

        existing = cursor.fetchone()

        conn.close()

        if existing is None:
            return code


# GET ALL PARTICIPANTS

def get_all_participants():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name, code, recipient, revealed
        FROM participants
        ORDER BY name
    """)

    participants = cursor.fetchall()

    conn.close()

    return participants


# GET ONE PARTICIPANT

def get_participant(code):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name, code, recipient, revealed
        FROM participants
        WHERE code = ?
    """, (code,))

    participant = cursor.fetchone()

    conn.close()

    return participant


# MARK PARTICIPANT AS REVEALED

def mark_revealed(code):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE participants
        SET revealed = 1
        WHERE code = ?
    """, (code,))

    conn.commit()
    conn.close()


# GENERATE SECRET SANTA ASSIGNMENTS

def generate_assignments(names):

    if len(names) < 2:
        return None

    for _ in range(5000):

        shuffled = names.copy()

        random.shuffle(shuffled)

        if all(
            names[i] != shuffled[i]
            for i in range(len(names))
        ):

            assignments = {}

            for i in range(len(names)):
                assignments[names[i]] = shuffled[i]

            return assignments

    return None


# SAVE / REGENERATE ENTIRE RAFFLE

def save_raffle(names):

    assignments = generate_assignments(names)

    if assignments is None:
        return False

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT name, code FROM participants"
    )

    existing_codes = {
        row[0]: row[1]
        for row in cursor.fetchall()
    }

    cursor.execute(
        "DELETE FROM participants"
    )

    for name in names:

        if name in existing_codes:

            code = existing_codes[name]

        else:

            code = generate_code()

        cursor.execute("""
            INSERT INTO participants
            (name, code, recipient, revealed)
            VALUES (?, ?, ?, 0)
        """, (
            name,
            code,
            assignments[name]
        ))

    conn.commit()
    conn.close()

    return True


# ADD PARTICIPANTS WITHOUT RESHUFFLING REVEALED ASSIGNMENTS

def add_participants_preserve_revealed(new_names):

    participants = get_all_participants()

    existing_names = {
        row[1]
        for row in participants
    }

    new_names = [
        name for name in new_names
        if name not in existing_names
    ]

    if not new_names:
        return False, "No new participants were added."

    conn = get_connection()
    cursor = conn.cursor()

    try:

        current_participants = get_all_participants()

        unrevealed = [
            row for row in current_participants
            if row[4] == 0
        ]

        revealed = [
            row for row in current_participants
            if row[4] == 1
        ]

        # If everyone has already revealed, adding someone would
        # require changing at least one revealed assignment.
        if revealed and not unrevealed:
            conn.close()
            return False, (
                "Everyone has already revealed their assignment. "
                "A new participant cannot be added without changing "
                "at least one revealed assignment."
            )

        # If there are no existing participants, this is not enough
        # to create a raffle yet.
        if not current_participants and len(new_names) < 2:
            conn.close()
            return False, "You need at least 2 participants."

        # If there are no revealed assignments, create a normal raffle.
        if not revealed:

            all_names = [
                row[1]
                for row in current_participants
            ] + new_names

            assignments = generate_assignments(all_names)

            if assignments is None:
                conn.close()
                return False, "Could not generate valid assignments."

            existing_codes = {
                row[1]: row[2]
                for row in current_participants
            }

            cursor.execute("DELETE FROM participants")

            for name in all_names:

                if name in existing_codes:
                    code = existing_codes[name]
                else:
                    code = generate_code()

                cursor.execute("""
                    INSERT INTO participants
                    (name, code, recipient, revealed)
                    VALUES (?, ?, ?, 0)
                """, (
                    name,
                    code,
                    assignments[name]
                ))

            conn.commit()
            conn.close()

            return True, (
                f"Added {len(new_names)} participant(s) "
                "and generated the raffle."
            )

        # There is at least one unrevealed participant.
        # We create a chain so that revealed assignments never change.
        #
        # Before:
        #     A -> B
        #
        # After adding New:
        #     A -> New
        #     New -> B
        #
        # If another person is added:
        #     A -> New1
        #     New1 -> New2
        #     New2 -> B
        #
        # This changes only unrevealed assignments.

        unrevealed = [
            row for row in current_participants
            if row[4] == 0
        ]

        chain_person = random.choice(unrevealed)

        chain_person_name = chain_person[1]
        chain_recipient = chain_person[3]

        for new_name in new_names:

            new_code = generate_code()

            cursor.execute("""
                UPDATE participants
                SET recipient = ?
                WHERE name = ?
                AND revealed = 0
            """, (
                new_name,
                chain_person_name
            ))

            cursor.execute("""
                INSERT INTO participants
                (name, code, recipient, revealed)
                VALUES (?, ?, ?, 0)
            """, (
                new_name,
                new_code,
                chain_recipient
            ))

            # The newly added participant becomes the next link
            # in the chain.
            chain_person_name = new_name

        conn.commit()
        conn.close()

        return True, (
            f"Added {len(new_names)} participant(s). "
            "All revealed assignments were kept unchanged. "
            "Only unrevealed assignments were adjusted."
        )

    except Exception as error:

        conn.rollback()
        conn.close()

        return False, f"Could not add participants: {error}"


# RESHUFFLE ONLY UNREVEALED PARTICIPANTS

def reshuffle_unrevealed():

    participants = get_all_participants()

    if len(participants) < 2:
        return False

    revealed = [
        row for row in participants
        if row[4] == 1
    ]

    unrevealed = [
        row for row in participants
        if row[4] == 0
    ]

    if len(unrevealed) < 2:
        return False

    used_recipients = {
        row[3]
        for row in revealed
    }

    available_recipients = [
        row[1]
        for row in participants
        if row[1] not in used_recipients
    ]

    if len(available_recipients) != len(unrevealed):
        return False

    for _ in range(5000):

        shuffled = available_recipients.copy()

        random.shuffle(shuffled)

        valid = True

        for i in range(len(unrevealed)):

            person = unrevealed[i][1]
            recipient = shuffled[i]

            if person == recipient:

                valid = False
                break

        if valid:

            conn = get_connection()
            cursor = conn.cursor()

            for i in range(len(unrevealed)):

                person = unrevealed[i][1]
                recipient = shuffled[i]

                cursor.execute("""
                    UPDATE participants
                    SET recipient = ?
                    WHERE name = ?
                    AND revealed = 0
                """, (
                    recipient,
                    person
                ))

            conn.commit()
            conn.close()

            return True

    return False


# DELETE ENTIRE RAFFLE

def delete_raffle():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM participants"
    )

    conn.commit()
    conn.close()


# SESSION STATE

if "organizer_logged_in" not in st.session_state:

    st.session_state.organizer_logged_in = False


if "pending_change" not in st.session_state:

    st.session_state.pending_change = None


# TITLE

st.title("🎄 Secret Santa 2026")

st.write(
    "Class of 2027 get your secret santa"
)


# ORGANIZER LOGIN

with st.sidebar:

    st.header("🎅 Admin")

    if not st.session_state.organizer_logged_in:

        password = st.text_input(
            "Organizer Password",
            type="password"
        )

        if st.button("Login"):

            if password == ORGANIZER_PASSWORD:

                st.session_state.organizer_logged_in = True

                st.success(
                    "Organizer login successful!"
                )

                st.rerun()

            else:

                st.error(
                    "Incorrect password."
                )

    else:

        st.success(
            "Organizer logged in"
        )

        if st.button("Logout"):

            st.session_state.organizer_logged_in = False

            st.rerun()


# PARTICIPANT REVEAL

st.header("🎁 Find Your Secret Santa")

code = st.text_input(
    "Enter your Secret Santa code",
    max_chars=6
).strip().upper()


if st.button("Reveal My Secret Santa"):

    if not code:

        st.warning(
            "Please enter your Secret Santa code."
        )

    else:

        participant = get_participant(code)

        if participant is None:

            st.error(
                "Invalid code. Please check your code."
            )

        else:

            (
                participant_id,
                name,
                participant_code,
                recipient,
                revealed
            ) = participant

            mark_revealed(code)

            st.success(
                f"🎁 {name}, your Secret Santa recipient is:"
            )

            st.subheader(
                f"🎄 {recipient}"
            )

            st.balloons()

            st.info(
                "Your organizer can change the raffle later. "
                "If the raffle is changed, your assignment "
                "may change."
            )


# ORGANIZER DASHBOARD

if st.session_state.organizer_logged_in:

    st.divider()

    st.header("🎅 Organizer Dashboard")


    # ADD PARTICIPANTS

    st.subheader("➕ Add Participants")

    new_names_text = st.text_area(
        "Enter new names, one per line",
        placeholder="John\nMary\nDavid"
    )

    if st.button("Add Participants"):

        new_names = [
            name.strip()
            for name in new_names_text.splitlines()
            if name.strip()
        ]

        if not new_names:

            st.warning(
                "Please enter at least one new participant."
            )

        else:

            success, message = add_participants_preserve_revealed(
                new_names
            )

            if success:

                st.success(message)

                st.info(
                    "Revealed assignments were kept unchanged. "
                    "Only unrevealed assignments may have been adjusted."
                )

                st.rerun()

            else:

                st.error(message)


    # CURRENT PARTICIPANTS

    st.subheader(
        "👥 Current Participants"
    )

    participants = get_all_participants()

    if not participants:

        st.info(
            "No participants yet."
        )

    else:

        for participant in participants:

            (
                participant_id,
                name,
                code,
                recipient,
                revealed
            ) = participant

            col1, col2, col3 = st.columns(
                [3, 2, 1]
            )

            with col1:

                st.write(
                    f"**{name}**"
                )

            with col2:

                st.code(code)

            with col3:

                if st.button(
                    "🗑️",
                    key=f"delete_{participant_id}"
                ):

                    current_participants = (
                        get_all_participants()
                    )

                    names = [
                        row[1]
                        for row in current_participants
                    ]

                    remaining_names = [
                        n
                        for n in names
                        if n != name
                    ]

                    if len(remaining_names) < 2:

                        st.error(
                            "You need at least 2 "
                            "participants."
                        )

                    else:

                        revealed_people = [
                            row[1]
                            for row in current_participants
                            if row[4] == 1
                        ]

                        st.session_state.pending_change = {

                            "type": "delete",

                            "name": name,

                            "remaining_names":
                                remaining_names,

                            "revealed_people":
                                revealed_people
                        }

                        st.rerun()


    # REMOVE WARNING

    if (
        st.session_state.pending_change
        and
        st.session_state.pending_change["type"]
        == "delete"
    ):

        change = (
            st.session_state.pending_change
        )

        st.divider()

        st.warning(
            f"⚠️ You are about to remove "
            f"**{change['name']}**."
        )

        if change["revealed_people"]:

            st.write(
                "Some participants have already "
                "revealed their assignments."
            )

            st.write(
                "Removing this participant will "
                "regenerate the raffle, so "
                "**revealed assignments may change.**"
            )

            st.write(
                "**People who have already revealed:**"
            )

            for person in change[
                "revealed_people"
            ]:

                st.write(
                    f"- {person}"
                )

        else:

            st.write(
                "Removing this participant will "
                "regenerate the raffle."
            )

        st.write(
            "Do you want to continue?"
        )

        col1, col2 = st.columns(2)

        with col1:

            if st.button(
                "Yes, Remove & Reassign",
                key="confirm_delete"
            ):

                save_raffle(
                    change["remaining_names"]
                )

                st.session_state.pending_change = None

                st.success(
                    f"{change['name']} was removed "
                    "and the raffle was reassigned."
                )

                st.rerun()

        with col2:

            if st.button(
                "Cancel",
                key="cancel_delete"
            ):

                st.session_state.pending_change = None

                st.rerun()


    # RAFFLE STATUS

    st.divider()

    st.subheader(
        "📊 Raffle Status"
    )

    participants = get_all_participants()

    if participants:

        total = len(participants)

        revealed_count = sum(
            row[4] == 1
            for row in participants
        )

        st.write(
            f"👥 Total participants: "
            f"**{total}**"
        )

        st.write(
            f"🎁 Assignments revealed: "
            f"**{revealed_count}/{total}**"
        )

    else:

        st.info(
            "The raffle has not been created yet."
        )


    # WHO HAS WHO

    st.divider()

    st.subheader(
        "🔐 Who Has Who"
    )

    participants = get_all_participants()

    if participants:

        st.warning(
            "This information is private. "
            "Only the organizer should see it."
        )

        for participant in participants:

            (
                participant_id,
                name,
                code,
                recipient,
                revealed
            ) = participant

            if revealed:

                status = "✅ Revealed"

            else:

                status = "🔒 Not revealed"

            st.write(
                f"**{name}** → **{recipient}** "
                f"({status})"
            )

    else:

        st.info(
            "No assignments yet."
        )


    # RESHUFFLE RAFFLE

    st.divider()

    st.subheader(
        "🎲 Reshuffle Raffle"
    )

    participants = get_all_participants()

    if participants:

        st.write(
            "### 🎲 Reshuffle Everyone"
        )

        st.write(
            "Give everyone a completely new "
            "Secret Santa assignment."
        )

        if st.button(
            "🎲 Reshuffle Everyone",
            type="secondary"
        ):

            names = [
                row[1]
                for row in participants
            ]

            success = save_raffle(names)

            if success:

                st.success(
                    "🎲 Everyone has been given "
                    "a new Secret Santa!"
                )

                st.info(
                    "Everyone will need to reveal "
                    "their new assignment again."
                )

                st.rerun()

            else:

                st.error(
                    "Could not reshuffle the raffle."
                )


        st.write(
            "### 🔒 Reshuffle Unrevealed Only"
        )

        st.write(
            "People who have already revealed "
            "their Secret Santa will keep the "
            "same assignment."
        )

        if st.button(
            "🔒 Reshuffle Unrevealed Only",
            type="secondary"
        ):

            success = reshuffle_unrevealed()

            if success:

                st.success(
                    "🔒 The unrevealed participants "
                    "have been reshuffled."
                )

                st.info(
                    "Everyone who had already revealed "
                    "their assignment was left unchanged."
                )

                st.rerun()

            else:

                st.error(
                    "The unrevealed participants "
                    "could not be reshuffled while "
                    "keeping all revealed assignments "
                    "unchanged."
                )

    else:

        st.info(
            "There are no participants to reshuffle."
        )


    # RESET ENTIRE RAFFLE

    st.divider()

    st.subheader(
        "⚠️ Reset Raffle"
    )

    st.write(
        "This will delete everyone and "
        "start the raffle from the beginning."
    )

    if st.button(
        "🗑️ Delete Entire Raffle",
        type="secondary"
    ):

        delete_raffle()

        st.success(
            "The entire raffle has been deleted."
        )

        st.rerun()
