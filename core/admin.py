from django.contrib import admin
from .models import(
    Questionnaire,
    BFSTest,
    BFSTestFile,
    MeridianTest,
    MeridianReading,
    FaceDiagnosis,
)

admin.site.register(Questionnaire)
admin.site.register(BFSTest)
admin.site.register(BFSTestFile)
admin.site.register(MeridianTest)
admin.site.register(MeridianReading)
admin.site.register(FaceDiagnosis)