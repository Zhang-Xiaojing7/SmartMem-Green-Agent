from typing import Any
from pydantic import BaseModel, HttpUrl, ValidationError
from a2a.server.tasks import TaskUpdater
from a2a.types import Message, TaskState, Part, TextPart, DataPart
from a2a.utils import get_message_text, new_agent_text_message

from messenger import Messenger
from green_agent_v2 import AdaptiveGenerator, AdaptiveEvaluator


class EvalRequest(BaseModel):
    """Request format sent by the AgentBeats platform to green agents."""
    participants: dict[str, HttpUrl] # role -> agent URL
    config: dict[str, Any]


class Agent:
    """
    Green Agent Testing Pipeline.
    In this pipeline, the Green Agent acts as the examiner. It fetches questions, sends them to the examinee (Purple Agent), engages in necessary interactions, and finally collects and forwards the examinee's answers to the grader.

    Upon receiving new question sets generated based on the examinee's identified weaknesses from the grading process, the Green Agent continues to administer questions until the maximum number of test rounds is reached. Finally, the Green Agent returns the examinee's evaluation results.

    The following configurations are required in scenario.toml:

    - max_test_rounds: Specifies the maximum number of test rounds. Each test round consists of one instruction issued by the Green Agent.
    - targeted_per_weakness: The number of questions generated for each identified weakness category after evaluation. For example, if set to 3 and the examinee reveals 2 weaknesses, 6 new questions will be generated.
    - convergence_threshold: The convergence threshold (testing stops when the change in pass rate between two consecutive rounds is less than this value).
    """
    required_roles: list[str] = ['purple']
    required_config_keys: list[str] = ['max_test_rounds', 'targeted_per_weakness', 'convergence_threshold']

    def __init__(self):
        self.messenger = Messenger()
        self.test_case_generator = AdaptiveGenerator()
        self.evaluator = AdaptiveEvaluator()

    def validate_request(self, request: EvalRequest) -> tuple[bool, str]:
        missing_roles = set(self.required_roles) - set(request.participants.keys())
        if missing_roles:
            return False, f"Missing roles: {missing_roles}"

        missing_config_keys = set(self.required_config_keys) - set(request.config.keys())
        if missing_config_keys:
            return False, f"Missing config keys: {missing_config_keys}"

        # Add additional request validation here

        return True, "ok"

    async def run(self, message: Message, updater: TaskUpdater) -> None:
        """
        Args:
            message: The incoming message
            updater: Report progress (update_status) and results (add_artifact)

        Use self.messenger.talk_to_agent(message, url) to call other agents.
        """
        input_text = get_message_text(message)

        try:
            request: EvalRequest = EvalRequest.model_validate_json(input_text)
            ok, msg = self.validate_request(request)
            if not ok:
                await updater.reject(new_agent_text_message(msg))
                return
        except ValidationError as e:
            await updater.reject(new_agent_text_message(f"Invalid request: {e}"))
            return

        purple_addr = request.participants['purple']
        max_rounds = request.config['max_test_rounds']
        target_count = request.config['targeted_per_weakness']
        threshold = request.config['convergence_threshold']
        
        #TODO: adaptive test loop

        await updater.update_status(
            TaskState.working, new_agent_text_message("Thinking...")
        )
        await updater.add_artifact(
            parts=[
                Part(root=TextPart(text="The agent performed well.")),
                Part(root=DataPart(data={
                    # structured assessment results
                }))
            ],
            name="Result",
        )