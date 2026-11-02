"""Review UI: run the agent, edit and approve each answer, export, and (with confirmation) update the CRM.

    .venv/bin/streamlit run app.py
"""
import json

import streamlit as st

from rfp import audit, config, crm, draft, knowledge, library, llm, permissions, pipeline

st.set_page_config(page_title="RFP Response Agent", layout="wide")
USERS = permissions.load_users()
RFPS = sorted(p.stem for p in config.RFPS.glob("*.txt"))
CHUNKS = {c["id"]: c for c in knowledge.load_chunks()}


def md(text):
    """Escape '$' so Streamlit shows prices instead of reading "$55 ... $10" as a math formula."""
    return text.replace("$", "\\$")


@st.cache_resource
def index():
    return pipeline.build_index()          # embeddings are computed once per session (and cached on disk)


# --- Sidebar: choose an RFP and who is reviewing -------------------------------------
with st.sidebar:
    st.header("RFP Response Agent")
    rfp_name = st.selectbox("RFP", RFPS)
    user_id = st.selectbox("Reviewer", list(USERS), format_func=lambda u: f"{USERS[u]['name']} ({USERS[u]['role']})")
    if st.button("Run agent", type="primary", use_container_width=True):
        if not llm.has_key():
            st.error(llm.MISSING_KEY)
            st.stop()
        for key in [k for k in st.session_state if k.startswith(("ans_", "dec_"))]:
            del st.session_state[key]                       # a new run starts with fresh answers
        with st.spinner("Reading the RFP, searching documents, assessing each requirement..."):
            st.session_state.result = pipeline.run(rfp_name, user_id, index=index(), log=lambda *_: None)
            st.session_state.decisions = {}
        audit.log("run", USERS[user_id]["name"], rfp=rfp_name)
    st.caption("Nothing is sent to the customer. The CRM is only updated after you confirm.")

result = st.session_state.get("result")
if not result:
    st.info("Pick an RFP and a reviewer, then click **Run agent**.")
    st.text((config.RFPS / f"{rfp_name}.txt").read_text())
    st.stop()
if result["rfp"] != rfp_name or result["user"]["id"] != user_id:
    st.warning(f"Showing results for **{result['rfp']}** as **{result['user']['name']}**. Click Run agent to refresh.")

user, rows, decisions = result["user"], result["rows"], st.session_state.decisions

# --- Overview ------------------------------------------------------------------------
st.title(f"{result['customer']}: draft RFP response")
n = draft.counts(rows)
cols = st.columns(4)
for col, status in zip(cols, ["supported", "conditional", "not_supported", "not_found"]):
    col.metric(draft.ICON[status], n[status])
if result["hidden"]:
    st.caption(f"🔒 {result['hidden']} document sections were hidden by {user['name']}'s permissions.")
if result["summary"]:
    with st.expander("Deal summary (internal)", expanded=True):
        st.markdown(md(result["summary"]))
        st.caption(f"Looked up by the agent: {', '.join(result['calls']) or 'nothing'}")


def decide(rid, row):
    """Called when a reviewer changes a decision: log it, and keep the answer library in step with it.
    Only the latest decision counts: Reject or Pending withdraws an earlier approval."""
    choice = st.session_state[f"dec_{rid}"]
    answer = st.session_state[f"ans_{rid}"]
    decisions[rid] = choice
    edited = answer != row["answer"]
    audit.log(f"decision_{choice.lower()}", user["name"], rfp=result["rfp"], requirement=rid, edited=edited)
    source = f"{result['rfp']}:{rid}"
    if choice == "Approve":
        entry = library.add({**row, "answer": answer}, user["name"], source)
        st.toast(f"{rid} approved and saved to the answer library as {entry['id']}.")
    elif library.remove(source):
        st.toast(f"{rid}: approval withdrawn and removed from the answer library.")


# --- One card per requirement, riskiest first ----------------------------------------
st.subheader("Requirements")
for r in sorted(rows, key=lambda r: draft.ORDER[r["status"]]):
    rid = r["id"]
    with st.container(border=True):
        st.markdown(f"**{rid}** · {draft.ICON[r['status']]}  \n{md(r['text'])}")
        st.text_area("Answer to the customer", r["answer"], key=f"ans_{rid}", height=90)
        if r["conditions"]:
            st.markdown(f"**Conditions (internal):** {md(r['conditions'])}")
        if r.get("conflict"):
            st.warning(f"⚡ Conflicting sources: {md(r['conflict'])}")
        if r.get("reused_from"):
            st.caption(f"♻️ Reused approved answer {r['reused_from']}")
        if r.get("library_note"):
            st.caption(f"Library: {r['library_note']}")
        ids = r["citations"] if r["status"] != "not_found" else r["searched"]
        with st.expander("Evidence" if r["status"] != "not_found" else "Searched (no match)"):
            for cid in ids:
                c = CHUNKS[cid]
                st.markdown(f"**{cid}** · updated {c['updated']} · owner {c['owner']}")
                st.text(c["text"])
        left, right = st.columns([3, 2])
        left.caption(f"Confirm with: {r['owner']}" if r["owner"] else "No reviewer needed")
        right.radio("Decision", ["Pending", "Approve", "Reject"], key=f"dec_{rid}", horizontal=True,
                    label_visibility="collapsed", on_change=decide, args=(rid, r))

# --- Export: only when every answer is approved --------------------------------------
st.subheader("Export")
pending = [r["id"] for r in rows if decisions.get(r["id"]) != "Approve"]
if pending:
    st.info(f"{len(pending)} answers still need approval: {', '.join(pending)}")
else:
    answers = {r["id"]: st.session_state["ans_" + r["id"]] for r in rows}      # the edited, approved text
    final = "\n\n".join([f"# Response to {result['customer']}"] +
                        [f"**{r['id']}** {r['text']}\n\n{answers[r['id']]}" for r in rows])
    st.download_button("Download customer response (.md)", final, file_name=f"response_{result['rfp']}.md")
    st.caption("Only the approved answers go out. Conditions and internal notes are not included.")

# --- CRM write: show exactly what will be written, then confirm ----------------------
st.subheader("Update CRM")
update = crm.propose_update(result["customer"], rows)
st.code(json.dumps(update, indent=2), language="json")
confirm = st.checkbox("I have reviewed this update")
if st.button("Write to CRM", disabled=not confirm):
    path, written = crm.write_update(update, user["name"])
    if written:
        st.success(f"Written to {path.name} (simulated CRM).")
    else:
        st.info("This exact update is already in the CRM. Nothing was written again.")
