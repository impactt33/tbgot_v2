from dishka import Provider, Scope, provide

from main.domain.use_cases import GenerateSourcePostUseCase, GenerateQuizUseCase, PublishPostUseCase, \
    PreviewPostUseCase, ChangeUserRoleUseCase, DiscardDraftUseCase
from main.domain.use_cases.create_custom_post import CreateCustomPostUseCase


class UseCaseProvider(Provider):
    scope = Scope.REQUEST

    generate_quiz = provide(GenerateQuizUseCase)
    generate_material_post = provide(GenerateSourcePostUseCase)
    publish_post = provide(PublishPostUseCase)
    preview_post = provide(PreviewPostUseCase)
    change_role = provide(ChangeUserRoleUseCase)
    discard_draft = provide(DiscardDraftUseCase)
    create_custom_post = provide(CreateCustomPostUseCase)