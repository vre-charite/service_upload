from enum import Enum
from ..commons.data_providers import SessionJob


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


class FsmMgrUpload(SessionJob):
    '''
    State manager for uplaod
    '''

    def go(self, target: EState):
        '''
        set status
        '''
        self.set_status(target.name)
        return self.save()
