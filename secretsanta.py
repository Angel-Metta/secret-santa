import streamlit as st
import sqlite3
import random
import string


# ==========================================
# PAGE CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="Secret Santa 2026",
    page_icon="🎄",
    layout="centered"
)


# ==========================================
# DATABASE
# ==========================================

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


# ==========================================
# ORGANIZER PASSWORD
# ==========================================

ORGANIZER_PASSWORD = "Santa2026"


# ==========================================
# GENERATE UNIQUE CODE
# ==========================================

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


# ==========================================
# GET ALL PARTICIPANTS
# ==========================================

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


# ==========================================
# GET ONE PARTICIPANT
# ==========================================

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


# ==========================================
# MARK PARTICIPANT AS REVEALED
# ==========================================

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


# ==========================================
# GENERATE SECRET SANTA ASSIGNMENTS
# ==========================================

def generate_assignments(names):

    if len(names) < 2:
        return None

    shuffled = names.copy()

    while True:

        random.shuffle(shuffled)

        # Nobody can get themselves
        if all(
            names[i] != shuffled[i]
            for i in range(len(names))
        ):
            break

    assignments = {}

    for i in range(len(names)):
        assignments[names[i]] = shuffled[i]

    return assignments


# ==========================================
# SAVE / REGENERATE RAFFLE
# ==========================================

def save_raffle(names):

    assignments = generate_assignments(names)

    if assignments is None:
        return False

    conn = get_connection()
    cursor = conn.cursor()

    # Save existing participant codes
    cursor.execute(
        "SELECT name, code FROM participants"
    )

    existing_codes = {
        row[0]: row[1]
        for row in cursor.fetchall()
    }

    # Remove old assignments
    cursor.execute(
        "DELETE FROM participants"
    )

    # Create new assignments
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


# ==========================================
# DELETE ENTIRE RAFFLE
# ==========================================

def delete_raffle():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM participants"
    )

    conn.commit()
    conn.close()


# ==========================================
# SESSION STATE
# ==========================================

if "organizer_logged_in" not in st.session_state:
    st.session_state.organizer_logged_in = False


if "pending_change" not in st.session_state:
    st.session_state.pending_change = None


# ==========================================
# TITLE
# ==========================================

st.title("🎄 Secret Santa 2026")

st.write(
    "Digital Secret Santa for the class"
)


# ==========================================
# ORGANIZER LOGIN
# ==========================================

with st.sidebar:

    st.header("🎅 Organizer")

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


# ==========================================
# PARTICIPANT REVEAL
# ==========================================

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

            # Record that the person revealed
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


# ==========================================
# ORGANIZER DASHBOARD
# ==========================================

if st.session_state.organizer_logged_in:

    st.divider()

    st.header("🎅 Organizer Dashboard")


    # ======================================
    # ADD PARTICIPANTS
    # ======================================

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

        participants = get_all_participants()

        existing_names = [
            row[1]
            for row in participants
        ]

        # Remove duplicates
        names_to_add = [
            name
            for name in new_names
            if name not in existing_names
        ]

        if not names_to_add:

            st.warning(
                "No new participants were added."
            )

        else:

            all_names = (
                existing_names +
                names_to_add
            )

            if len(all_names) < 2:

                st.warning(
                    "You need at least 2 participants."
                )

            else:

                revealed_people = [
                    row[1]
                    for row in participants
                    if row[4] == 1
                ]

                if revealed_people:

                    st.session_state.pending_change = {

                        "type": "add",

                        "names": all_names,

                        "added": names_to_add,

                        "revealed_people":
                            revealed_people
                    }

                    st.rerun()

                else:

                    save_raffle(
                        all_names
                    )

                    st.success(
                        f"Added {len(names_to_add)} "
                        f"participant(s) and generated "
                        f"new assignments."
                    )

                    st.rerun()


    # ======================================
    # ADD WARNING
    # ======================================

    if (
        st.session_state.pending_change
        and
        st.session_state.pending_change["type"]
        == "add"
    ):

        change = (
            st.session_state.pending_change
        )

        st.warning(
            "⚠️ Some participants have already "
            "revealed their Secret Santa."
        )

        st.write(
            "Adding new participants will "
            "regenerate the raffle."
        )

        st.write(
            "**Their assignments may change:**"
        )

        for person in change[
            "revealed_people"
        ]:

            st.write(
                f"- {person}"
            )

        st.write(
            "Do you want to continue?"
        )

        col1, col2 = st.columns(2)


        with col1:

            if st.button(
                "Yes, Add & Reassign",
                key="confirm_add"
            ):

                save_raffle(
                    change["names"]
                )

                st.session_state.pending_change = None

                st.success(
                    "Participants added and "
                    "the raffle was reassigned."
                )

                st.rerun()


        with col2:

            if st.button(
                "Cancel",
                key="cancel_add"
            ):

                st.session_state.pending_change = None

                st.rerun()


    # ======================================
    # CURRENT PARTICIPANTS
    # ======================================

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


    # ======================================
    # REMOVE WARNING
    # ======================================

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


    # ======================================
    # RAFFLE STATUS
    # ======================================

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


    # ======================================
    # WHO HAS WHO
    # ======================================

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


    # ======================================
    # RESHUFFLE RAFFLE
    # ======================================

    st.divider()

    st.subheader(
        "🎲 Reshuffle Raffle"
    )

    st.write(
        "Generate completely new Secret Santa "
        "assignments for everyone."
    )

    participants = get_all_participants()


    if participants:

        revealed_people = [
            row[1]
            for row in participants
            if row[4] == 1
        ]


        if st.button(
            "🎲 Reshuffle Raffle",
            type="secondary"
        ):

            names = [
                row[1]
                for row in participants
            ]


            if revealed_people:

                st.session_state.pending_change = {

                    "type": "reshuffle",

                    "names": names,

                    "revealed_people":
                        revealed_people
                }

                st.rerun()

            else:

                save_raffle(names)

                st.success(
                    "🎲 The raffle has been reshuffled!"
                )

                st.rerun()


    # ======================================
    # RESHUFFLE WARNING
    # ======================================

    if (
        st.session_state.pending_change
        and
        st.session_state.pending_change["type"]
        == "reshuffle"
    ):

        change = (
            st.session_state.pending_change
        )

        st.warning(
            "⚠️ Some participants have already "
            "revealed their Secret Santa."
        )

        st.write(
            "Reshuffling will give everyone a "
            "completely new assignment."
        )

        st.write(
            "**Their revealed assignments "
            "will change:**"
        )


        for person in change[
            "revealed_people"
        ]:

            st.write(
                f"- {person}"
            )


        st.write(
            "Do you want to continue?"
        )

        col1, col2 = st.columns(2)


        with col1:

            if st.button(
                "Yes, Reshuffle",
                key="confirm_reshuffle"
            ):

                save_raffle(
                    change["names"]
                )

                st.session_state.pending_change = None

                st.success(
                    "🎲 The raffle has been "
                    "completely reshuffled!"
                )

                st.rerun()


        with col2:

            if st.button(
                "Cancel",
                key="cancel_reshuffle"
            ):

                st.session_state.pending_change = None

                st.rerun()


    # ======================================
    # RESET ENTIRE RAFFLE
    # ======================================

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