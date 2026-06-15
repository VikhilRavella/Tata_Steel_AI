from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
import json
from sqlalchemy.orm import Session
import backend.models as models
from backend.services.ollama_service import generate_completion_sync
DISCOVERY_PROMPT = 'You are a highly analytical Senior Engineering Architect.\nYour task is to review the current Requirement Profile for a project and the user\'s latest input, then determine if all necessary requirements have been gathered.\n\nCURRENT REQUIREMENT PROFILE:\nProject Name: {project_name}\nProblem Statement: {problem_statement}\nBusiness Goal: {business_goal}\nExpected Outcome: {expected_outcome}\nTech Stack: {tech_stack}\nConstraints: {constraints}\nTimeline: {timeline}\n\nUSER\'S LATEST MESSAGE:\n{user_message}\n\nINSTRUCTIONS:\n1. Extract any new information from the User\'s Latest Message and map it to the missing fields in the Requirement Profile.\n2. If any critical fields (Problem Statement, Business Goal, Expected Outcome, Constraints) are still empty or vague, you MUST ask a clarification question.\n3. If all critical fields are sufficiently defined, mark the status as "complete".\n\nReturn a strictly valid JSON response in the following format:\n{{\n  "updated_fields": {{\n    "problem_statement": "string or null",\n    "business_goal": "string or null",\n    "expected_outcome": "string or null",\n    "tech_stack": "string or null",\n    "constraints": "string or null",\n    "timeline": "string or null"\n  }},\n  "status": "gathering" or "complete",\n  "clarification_question": "string (your question to the user, or null if complete)"\n}}\n'

async def process_requirements(session_id: str, user_message: str, db: AsyncSession) -> dict:
    profile = (db.execute(select(models.RequirementProfile).where(models.RequirementProfile.session_id == session_id))).scalars().first()
    if not profile:
        return {'status': 'complete', 'message': None}
    if profile.status == 'complete':
        return {'status': 'complete', 'message': None}
    prompt = DISCOVERY_PROMPT.format(project_name=profile.project_name or 'None', problem_statement=profile.problem_statement or 'None', business_goal=profile.business_goal or 'None', expected_outcome=profile.expected_outcome or 'None', tech_stack=profile.tech_stack or 'None', constraints=profile.constraints or 'None', timeline=profile.timeline or 'None', user_message=user_message)
    llm_response = await generate_completion_sync(prompt, model='qwen2.5-coder:7b')
    try:
        if '```json' in llm_response:
            json_str = llm_response.split('```json')[1].split('```')[0].strip()
            data = json.loads(json_str)
        else:
            data = json.loads(llm_response)
        updates = data.get('updated_fields', {})
        if updates.get('problem_statement'):
            profile.problem_statement = updates['problem_statement']
        if updates.get('business_goal'):
            profile.business_goal = updates['business_goal']
        if updates.get('expected_outcome'):
            profile.expected_outcome = updates['expected_outcome']
        if updates.get('tech_stack'):
            profile.tech_stack = updates['tech_stack']
        if updates.get('constraints'):
            profile.constraints = updates['constraints']
        if updates.get('timeline'):
            profile.timeline = updates['timeline']
        profile.status = data.get('status', 'gathering')
        db.commit()
        return {'status': profile.status, 'message': data.get('clarification_question')}
    except Exception as e:
        print(f'Error parsing discovery response: {e}')
        return {'status': 'gathering', 'message': 'I need a bit more clarification on your requirements before proceeding. Could you elaborate on your expected outcome and constraints?'}