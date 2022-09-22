# Copyright 2022 Indoc Research
# 
# Licensed under the EUPL, Version 1.2 or – as soon they
# will be approved by the European Commission - subsequent
# versions of the EUPL (the "Licence");
# You may not use this work except in compliance with the
# Licence.
# You may obtain a copy of the Licence at:
# 
# https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12
# 
# Unless required by applicable law or agreed to in
# writing, software distributed under the Licence is
# distributed on an "AS IS" basis,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
# express or implied.
# See the Licence for the specific language governing
# permissions and limitations under the Licence.
# 

from enum import Enum

from app.commons.data_providers import SessionJob


class EState(Enum):
    """Upload state."""

    INIT = (0,)
    PRE_UPLOADED = (1,)
    CHUNK_UPLOADED = (2,)
    FINALIZED = (3,)
    SUCCEED = (4,)
    TERMINATED = 5


class FsmMgrUpload(SessionJob):
    """State manager for uplaod."""

    async def go(self, target: EState):
        """set status."""
        try:
            self.set_status(target.name)
            return await self.save()
        except Exception:
            raise


async def get_fsm_object(*args):
    fms_object = FsmMgrUpload(*args)
    if fms_object.job_id:
        await fms_object.read()
    return fms_object
