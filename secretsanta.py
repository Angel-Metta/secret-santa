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
