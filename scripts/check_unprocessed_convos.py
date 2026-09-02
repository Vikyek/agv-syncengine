#!/usr/bin/env python3
import os
import sys
import json
import sqlite3
import argparse

HOME_DIR = os.path.expanduser("~")
DB_PATH = os.path.join(HOME_DIR, ".gemini/antigravity-cli/conversation_summaries.db")
STATE_PATH = os.path.join(HOME_DIR, ".gemini/antigravity-cli/synclearning_state.json")

def load_state():
    if os.path.exists(STATE_PATH):
        try:
            with open(STATE_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def get_unprocessed_jules_sessions():
    state = load_state()
    unprocessed = []
    
    # Check if agy-vules-integration is installed / available
    jules_path = os.path.join(HOME_DIR, "Projects/agy-vules-integration")
    if not os.path.exists(jules_path):
        return []
    
    sys.path.insert(0, jules_path)
    try:
        from jules_manager import list_sessions
        res = list_sessions()
        if not isinstance(res, dict) or "sessions" not in res:
            return []
        
        for session in res.get("sessions", []):
            sid = session.get("id") or session.get("name", "").split("/")[-1]
            state_val = session.get("state", "UNKNOWN")
            # We track jules sessions in state prefixed by 'jules_'
            key = f"jules_{sid}"
            recorded_state = state.get(key)
            if recorded_state is None or recorded_state != state_val:
                unprocessed.append({
                    "conversation_id": f"jules_{sid}",
                    "step_count": 1,
                    "title": session.get("title") or session.get("prompt", "")[:60].replace("\n", " "),
                    "is_jules": True,
                    "session_id": sid,
                    "jules_state": state_val
                })
    except Exception:
        pass
        
    return unprocessed

def get_unprocessed_convos(current_convo_id=None):
    if not os.path.exists(DB_PATH):
        unprocessed = []
    else:
        state = load_state()
        unprocessed = []
        
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT conversation_id, step_count FROM conversation_summaries")
            rows = cursor.fetchall()
            conn.close()
        except Exception as e:
            print(f"Error querying database: {e}", file=sys.stderr)
            rows = []

        for convo_id, step_count in rows:
            if current_convo_id and convo_id == current_convo_id:
                continue
            
            # Check if conversation transcript exists
            transcript_path = os.path.join(HOME_DIR, f".gemini/antigravity-cli/brain/{convo_id}/.system_generated/logs/transcript.jsonl")
            if not os.path.exists(transcript_path):
                continue
                
            recorded_steps = state.get(convo_id)
            if recorded_steps is None or step_count > recorded_steps:
                unprocessed.append({
                    "conversation_id": convo_id,
                    "step_count": step_count,
                    "is_jules": False
                })
            
    # Include unprocessed Jules sessions if agy-vules-integration is present
    jules_sessions = get_unprocessed_jules_sessions()
    unprocessed.extend(jules_sessions)

    return unprocessed

def test_script():
    print("Running self-tests...")
    convos = get_unprocessed_convos()
    print(f"Test succeeded. Found {len(convos)} unprocessed/updated conversations in DB.")

def main():
    parser = argparse.ArgumentParser(description="Scan and report conversations that need rule learning extraction.")
    parser.add_argument("--hook", action="store_true", help="Run as Antigravity lifecycle hook")
    parser.add_argument("--test", action="store_true", help="Run self-tests")
    args = parser.parse_args()

    if args.test:
        test_script()
        return 0

    current_convo_id = None
    if args.hook:
        try:
            context = json.loads(sys.stdin.read())
            current_convo_id = context.get("conversationId")
            # Only run on the very first invocation step to avoid spamming every turn
            if context.get("invocationNum", 0) > 1:
                print(json.dumps({}))
                return 0
        except Exception:
            pass

    unprocessed = get_unprocessed_convos(current_convo_id)

    if args.hook:
        if unprocessed:
            convo_list = ", ".join([c["conversation_id"] for c in unprocessed[:5]])
            if len(unprocessed) > 5:
                convo_list += " and others"
            
            warning_msg = (
                f"[Auto-Learning] The following conversations contain unprocessed learnings: {convo_list}. "
                "Please invoke a background worker subagent (Model: flash/pro) to run learning extraction on them, "
                f"update GEMINI.md in both {os.path.join(HOME_DIR, 'GEMINI.md')} and {os.path.join(HOME_DIR, '.gemini/config/GEMINI.md')}, sync the vault "
                f"using {os.path.join(HOME_DIR, '.gemini/config/sync_config_vault.sh')}, and run tag_conversations.py --mark-learned <convo_id> for each."
            )
            response = {
                "injectSteps": [
                    {
                        "ephemeralMessage": warning_msg
                    }
                ]
            }
            print(json.dumps(response))
        else:
            print(json.dumps({}))
    else:
        for c in unprocessed:
            print(f"{c['conversation_id']} (steps: {c['step_count']})")
            
    return 0

if __name__ == "__main__":
    sys.exit(main())
