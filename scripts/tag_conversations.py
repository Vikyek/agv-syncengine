#!/usr/bin/env python3
import os
import sys
import json
import sqlite3
import urllib.parse
import re

HOME_DIR = os.path.expanduser("~")
DB_PATH = os.path.join(HOME_DIR, ".gemini/antigravity-cli/conversation_summaries.db")
STATE_PATH = os.path.join(HOME_DIR, ".gemini/antigravity-cli/synclearning_state.json")

TAGS = ["DEV", "SYS", "DOC", "DOWN", "SUB", "LEARNED"]
_TAGS_REGEX = re.compile(r'\s*\[(?:' + '|'.join(re.escape(tag) for tag in TAGS) + r')\]\s*')
_MULTI_SPACE_REGEX = re.compile(r'\s+')
# ⚡ Bolt: Pre-compile regex for title updates to prevent dynamic compilation in loops
_PBTXT_TITLE_REGEX = re.compile(r'title\s*:\s*".*?"')

def strip_existing_tags(title):
    if not title:
        return ""
    # Remove tags from anywhere in the string
    cleaned = _TAGS_REGEX.sub(' ', title)
    # Collapse multiple spaces and strip
    cleaned = _MULTI_SPACE_REGEX.sub(' ', cleaned).strip()
    return cleaned

def get_path_from_uri(uri):
    if uri.startswith("file://"):
        return urllib.parse.unquote(uri[7:])
    return uri

def load_state():
    if os.path.exists(STATE_PATH):
        try:
            with open(STATE_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_state(state):
    try:
        with open(STATE_PATH, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"Error saving state: {e}", file=sys.stderr)

def mark_conversation_learned(convo_id):
    state = load_state()
    
    # Handle Jules session marking
    if convo_id.startswith("jules_"):
        sid = convo_id[6:]
        jules_path = os.path.join(HOME_DIR, "Projects/agy-vules-integration")
        jules_state = "PROCESSED"
        if os.path.exists(jules_path):
            sys.path.insert(0, jules_path)
            try:
                from jules_manager import _make_request
                sess = _make_request(f"sessions/{sid}")
                if isinstance(sess, dict) and "state" in sess:
                    jules_state = sess["state"]
            except Exception:
                pass
        state[convo_id] = jules_state
        save_state(state)
        print(f"Successfully marked Jules session {sid} as LEARNED at state '{jules_state}'")
        return

    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}", file=sys.stderr)
        sys.exit(1)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT step_count, title, workspace_uris, parent_conversation_id, nesting_depth FROM conversation_summaries WHERE conversation_id = ?",
        (convo_id,)
    )
    row = cursor.fetchone()
    if not row:
        print(f"Conversation {convo_id} not found in database", file=sys.stderr)
        conn.close()
        sys.exit(1)
    
    step_count, title, workspace_uris, parent_id, nesting_depth = row
    state[convo_id] = step_count
    save_state(state)
    
    # Run tag update logic to apply the tag immediately
    update_tags(conn, state)
    conn.close()
    print(f"Successfully marked conversation {convo_id} as LEARNED at step count {step_count}")

HISTORY_PATH = os.path.join(HOME_DIR, ".gemini/antigravity-cli/history.jsonl")

def get_last_commands():
    last_commands = {}
    if not os.path.exists(HISTORY_PATH):
        return last_commands
    ignore = {'/exit', '/quit', '/resume', '/clear', '/rewind'}
    try:
        with open(HISTORY_PATH, "r") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    convo_id = data.get("conversationId")
                    display = data.get("display", "").strip()
                    if convo_id and display:
                        # Check first word of display command
                        first_word = display.split()[0] if display.split() else ""
                        if first_word in ignore:
                            continue
                        last_commands[convo_id] = display
                except Exception:
                    pass
    except Exception:
        pass
    return last_commands

def determine_category(workspace_uris, parent_id, nesting_depth):
    """
    Determines the categorization tag for a conversation based on its context.

    @param workspace_uris - JSON string containing a list of workspace URIs
    @param parent_id - The ID of the parent conversation, if any
    @param nesting_depth - The depth of conversation nesting
    @returns A string representing the category tag (e.g., 'SUB', 'DOWN', 'DOC', 'SYS', 'DEV') or None if no category matches
    """
    # Determine category based on metadata
    if (parent_id and parent_id != "") or nesting_depth > 0:
        return "SUB"
    
    try:
        uris = json.loads(workspace_uris)
        if not uris:
            return None
        path = get_path_from_uri(uris[0])
    except Exception:
        return None
    
    downloads_dir = os.path.join(HOME_DIR, "Downloads")
    documents_dir = os.path.join(HOME_DIR, "Documents")
    config_dir = os.path.join(HOME_DIR, ".config")
    projects_dir = os.path.join(HOME_DIR, "Projects")

    if path.startswith(downloads_dir):
        return "DOWN"
    elif path.startswith(documents_dir) or "CVs" in path:
        return "DOC"
    elif path == HOME_DIR or path.startswith(config_dir) or path.startswith("/etc"):
        return "SYS"
    
    # Check for git repo or Projects directory
    if path.startswith(projects_dir) or os.path.isdir(os.path.join(path, ".git")):
        return "DEV"
        
    return None

ANNOTATIONS_DIR = os.path.join(HOME_DIR, ".gemini/antigravity-cli/annotations")
METADATA_CACHE_PATH = os.path.join(HOME_DIR, ".gemini/antigravity-cli/cache/conversation_metadata.json")

def update_pbtxt(convo_id, new_title):
    pbtxt_path = os.path.join(ANNOTATIONS_DIR, f"{convo_id}.pbtxt")
    if os.path.exists(pbtxt_path):
        try:
            with open(pbtxt_path, "r") as f:
                content = f.read()
            escaped_title = new_title.replace('"', '\\"')
            new_content = _PBTXT_TITLE_REGEX.sub(f'title:"{escaped_title}"', content)
            with open(pbtxt_path, "w") as f:
                f.write(new_content)
        except Exception as e:
            print(f"Error updating pbtxt for {convo_id}: {e}", file=sys.stderr)

def update_metadata_cache(convo_id, new_title):
    if os.path.exists(METADATA_CACHE_PATH):
        try:
            with open(METADATA_CACHE_PATH, "r") as f:
                data = json.load(f)
            convs = data.get("conversations", {})
            if convo_id in convs:
                updated = False
                if "summary" in convs[convo_id]:
                    convs[convo_id]["summary"]["Title"] = new_title
                    updated = True
                if "Title" in convs[convo_id]:
                    convs[convo_id]["Title"] = new_title
                    updated = True
                if updated:
                    with open(METADATA_CACHE_PATH, "w") as f:
                        json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error updating metadata cache for {convo_id}: {e}", file=sys.stderr)

def update_tags(conn, state):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT conversation_id, title, workspace_uris, parent_conversation_id, nesting_depth, step_count FROM conversation_summaries"
    )
    rows = cursor.fetchall()
    
    state_changed = False
    last_commands = get_last_commands()
    
    for row in rows:
        convo_id, title, workspace_uris, parent_id, nesting_depth, step_count = row
        base_title = strip_existing_tags(title)
        
        # Determine category tag
        category = determine_category(workspace_uris, parent_id, nesting_depth)
        
        # Auto-detect if last action was /learn
        if convo_id in last_commands:
            last_cmd = last_commands[convo_id]
            if last_cmd.startswith("/learn") and convo_id not in state:
                state[convo_id] = step_count
                state_changed = True
                
        # Check learned status
        has_learned = False
        if convo_id in state:
            recorded_steps = state[convo_id]
            last_cmd = last_commands.get(convo_id, "")
            is_rename = last_cmd.startswith("/rename")
            
            if step_count > recorded_steps:
                if is_rename:
                    # Rename command step. Persist learned status and update recorded step count.
                    state[convo_id] = step_count
                    state_changed = True
                    has_learned = True
                else:
                    # Real prompt step. Update state step count if user had already learned it previously or keep state.
                    has_learned = True
            else:
                has_learned = True
                
        # Reconstruct title - LEARNED is always first
        prefix = ""
        if has_learned:
            prefix += "[LEARNED]"
        if category:
            prefix += f"[{category}]"
            
        new_title = f"{prefix} {base_title}".strip() if prefix else base_title
        
        if new_title != title:
            cursor.execute(
                "UPDATE conversation_summaries SET title = ? WHERE conversation_id = ?",
                (new_title, convo_id)
            )
            update_pbtxt(convo_id, new_title)
            update_metadata_cache(convo_id, new_title)
            print(f"Updated: '{title}' -> '{new_title}'")
            
    conn.commit()
    if state_changed:
        save_state(state)

def main():
    if len(sys.argv) > 2 and sys.argv[1] == "--mark-learned":
        mark_conversation_learned(sys.argv[2])
    else:
        if not os.path.exists(DB_PATH):
            return
        conn = sqlite3.connect(DB_PATH)
        state = load_state()
        update_tags(conn, state)
        conn.close()

if __name__ == "__main__":
    main()
