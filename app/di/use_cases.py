from dishka import Provider, Scope, provide

from main.domain.use_cases import GenerateMaterialPostUseCase, GenerateQuizUseCase, PublishPostUseCase, \
    PreviewPostUseCase, ChangeUserRoleUseCase


class UseCaseProvider(Provider):
    scope = Scope.REQUEST

    generate_quiz = provide(GenerateQuizUseCase)
    generate_material_post = provide(GenerateMaterialPostUseCase)
    publish_post = provide(PublishPostUseCase)
    preview_post = provide(PreviewPostUseCase)
    change_role = provide(ChangeUserRoleUseCase)