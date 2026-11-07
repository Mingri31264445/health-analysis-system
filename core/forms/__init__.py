from .questionnaire import QuestionnaireForm
from .meridian import MeridianTestForm, MeridianTestUpdateForm
from .bfs import BFSTestForm, BFSTestUpdateForm
from .face_diagnosis import FaceDiagnosisForm, FaceDiagnosisUpdateForm
from .auth import RegisterForm, LoginForm, PhonePasswordResetForm

__all__ = [
    'QuestionnaireForm',
    'MeridianTestForm',
    'MeridianTestUpdateForm',
    'BFSTestForm',
    'BFSTestUpdateForm',
    'FaceDiagnosisForm',
    'FaceDiagnosisUpdateForm',
    'RegisterForm',
    'LoginForm',
    'PhonePasswordResetForm',
]