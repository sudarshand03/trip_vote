from collections import Counter, defaultdict
from itertools import combinations

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Trip Preference Vote", page_icon="🏔️")

DESTINATIONS = ["Tetons/Jackson Hole", "Banff", "San Francisco"]

ESTIMATED_COSTS = {
    "Tetons/Jackson Hole": 650,
    "Banff": 1000,
    "San Francisco": 950,
}

if "responses" not in st.session_state:
    st.session_state.responses = []

st.title("✈️ Group Trip Vote")
st.write("Rank the trips and enter your max budget.")

name = st.text_input("Your name")

ranking = st.multiselect(
    "Rank your preferences from best to worst",
    DESTINATIONS,
    max_selections=3,
)

budget = st.number_input(
    "Max total budget for Thursday-Monday ($)",
    min_value=0,
    step=50,
)

if st.button("Submit vote"):
    if not name:
        st.error("Please enter your name.")
    elif len(ranking) != 3:
        st.error("Please rank all three destinations.")
    elif budget <= 0:
        st.error("Please enter a valid budget.")
    else:
        st.session_state.responses = [
            r for r in st.session_state.responses if r["name"] != name
        ]
        st.session_state.responses.append(
            {
                "name": name,
                "ranking": ranking,
                "budget": budget,
            }
        )
        st.success("Vote submitted!")

st.divider()

st.subheader("Current responses")

if not st.session_state.responses:
    st.info("No votes yet.")
else:
    df = pd.DataFrame(
        [
            {
                "Name": r["name"],
                "1st": r["ranking"][0],
                "2nd": r["ranking"][1],
                "3rd": r["ranking"][2],
                "Max Budget": r["budget"],
            }
            for r in st.session_state.responses
        ]
    )
    st.dataframe(df, use_container_width=True)

    rankings = {r["name"]: r["ranking"] for r in st.session_state.responses}
    budgets = {r["name"]: r["budget"] for r in st.session_state.responses}

    feasible = [
        d
        for d in DESTINATIONS
        if all(ESTIMATED_COSTS[d] <= b for b in budgets.values())
    ]

    def borda_count(rankings, destinations):
        scores = defaultdict(int)
        n = len(destinations)

        for ranking in rankings.values():
            filtered = [d for d in ranking if d in destinations]
            for i, d in enumerate(filtered):
                scores[d] += n - i - 1

        return dict(scores)

    def pairwise_results(rankings, destinations):
        results = {}

        for a, b in combinations(destinations, 2):
            a_votes = 0
            b_votes = 0

            for ranking in rankings.values():
                filtered = [d for d in ranking if d in destinations]
                if filtered.index(a) < filtered.index(b):
                    a_votes += 1
                else:
                    b_votes += 1

            winner = a if a_votes > b_votes else b if b_votes > a_votes else None

            results[(a, b)] = {
                a: a_votes,
                b: b_votes,
                "winner": winner,
            }

        return results

    def condorcet_winner(rankings, destinations):
        results = pairwise_results(rankings, destinations)
        wins = Counter()

        for result in results.values():
            if result["winner"]:
                wins[result["winner"]] += 1

        for d in destinations:
            if wins[d] == len(destinations) - 1:
                return d

        return None

    def last_place_counts(rankings, destinations):
        counts = Counter()

        for ranking in rankings.values():
            filtered = [d for d in ranking if d in destinations]
            counts[filtered[-1]] += 1

        return dict(counts)

    st.divider()
    st.subheader("Results")

    st.write("Estimated costs:")
    st.json(ESTIMATED_COSTS)

    if not feasible:
        st.error("No destination is affordable for everyone.")
    else:
        borda = borda_count(rankings, feasible)
        last_places = last_place_counts(rankings, feasible)
        pairwise = pairwise_results(rankings, feasible)
        cw = condorcet_winner(rankings, feasible)

        if cw:
            winner = cw
            method = "Condorcet winner"
        else:
            winner = max(feasible, key=lambda d: (borda[d], -last_places.get(d, 0)))
            method = "Borda count fallback, with fewer last-place votes as tiebreaker"

        st.success(f"Winner: {winner}")
        st.write(f"Method: **{method}**")

        st.write("Feasible destinations:")
        st.write(feasible)

        st.write("Borda scores:")
        st.json(borda)

        st.write("Last-place counts:")
        st.json(last_places)

        st.write("Pairwise matchups:")
        for pair, result in pairwise.items():
            st.write(f"{pair[0]} vs {pair[1]}: {result}")

    if st.button("Clear all responses"):
        st.session_state.responses = []
        st.rerun()
