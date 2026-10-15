async def assign_xp(name: str, xp_awarded: int, commit_count: int, files_changed: int) -> str:
    """Award XP to an intern for a push.

    Call this once you've decided how much XP a push deserves, based
    on commit_count and files_changed.

    Args:
        name: The intern's GitHub username (must match pusher_name exactly)
        xp_awarded: XP to award for this push
        commit_count: Number of commits in the push
        files_changed: Number of distinct files touched

    Returns:
        Confirmation message with the intern's new total XP
    """
    payload = {"name": name, "xp_awarded": xp_awarded,
               "commit_count": commit_count, "files_changed": files_changed}
    response = await asyncio.to_thread(
        requests.post, f"{SERVER_URL}/xp", json=payload, timeout=10
    )
    response.raise_for_status()
    data = response.json()
    return f"Awarded {xp_awarded} XP to {name}. New total: {data['total_xp']}."


evaluator_agent = Agent(
    model=LiteLlm("groq/llama-3.3-70b-versatile"),
    name="evaluator_agent",
    description="Evaluates a GitHub push and awards XP to the intern who made it.",
    instruction=(
        "You evaluate one GitHub push and award XP to the intern who made it.\n"
        "You'll receive their name, commit count, and files changed.\n"
        "1. Decide a fair XP amount from commit_count and files_changed.\n"
        "2. Call assign_xp exactly once with the intern's name and your XP decision.\n"
        "Always use the provided tools rather than describing function calls in text."
    ),
    tools=[assign_xp],
)












class XPAward(BaseModel):
    name: str
    xp_awarded: int
    commit_count: int
    files_changed: int

@app.post("/xp")
def award_xp(xp: XPAward):
    data = r.get(LEADERBOARD_KEY)
    leaderboard = json.loads(data) if data else []

    for entry in leaderboard:
        if entry[1] == xp.name:
            entry[2] += xp.xp_awarded
            total_xp = entry[2]
            break
    else:
        raise HTTPException(status_code=404, detail=f"{xp.name} not on leaderboard — run seed_interns.py?")

    r.set(LEADERBOARD_KEY, json.dumps(leaderboard))
    return {"status": "awarded", "name": xp.name, "total_xp": total_xp}








from evaluator_agent_or_wherever import evaluator_agent  # or just reuse agent.py's import

evaluator_runner = InMemoryRunner(agent=evaluator_agent, app_name="xp_evaluator")

def is_known_intern(name: str) -> bool:
    data = r.get(LEADERBOARD_KEY)
    return bool(data) and name in {entry[1] for entry in json.loads(data)}

async def handle_push(pusher_name: str, message_text: str):
    if not is_known_intern(pusher_name):
        print(f"Ignoring push from {pusher_name} — not a tracked intern.")
        return

    session = await evaluator_runner.session_service.create_session(
        app_name="xp_evaluator", user_id=pusher_name
    )
    message = types.Content(role="user", parts=[types.Part(text=message_text)])

    async for event in evaluator_runner.run_async(
        user_id=pusher_name, session_id=session.id, new_message=message
    ):
        info = extract_event_info(event)
        if info:
            print(f"[{info['type']}]", info)








if event_type == "push":
    background_tasks.add_task(handle_push, facts["pusher_name"], message_text)