from enum import Enum
from ..resources.helpers import set_status, get_status


class EState(Enum):
    '''
    Upload state
    '''
    INIT = 0,
    PRE_UPLOADED = 1,
    CHUNK_UPLOADED = 2,
    FINALIZED = 3,
    SUCCEED = 4,
    TERMINATED = 5


class FsmMgrUpload():
    '''
    State manager for uplaod
    '''

    def __init__(self, session_id, job_id, file_full_path, project_code, operator):
        self.session_id = session_id
        self.job_id = job_id
        self.file_full_path = file_full_path
        self.project_code = project_code
        self.operator = operator
        self.payload = None

    def set_payload(self, payload):
        '''
        set payload
        '''
        self.payload = payload

    def go(self, target: EState):
        '''
        set status
        '''
        if not self.payload:
            self.payload = {}
        self.payload['file_full_path'] = self.file_full_path
        self.payload['resumable_identifier'] = self.job_id
        return set_status(
            self.session_id,
            self.job_id,
            self.file_full_path,
            "data_upload",
            target.name,
            self.project_code,
            self.operator,
            payload=self.payload
        )
