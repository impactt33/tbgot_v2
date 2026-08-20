from dishka import Provider, Scope, provide

from main.domain.use_cases import GenerateMaterialPostUseCase, GenerateQuizUseCase


class UseCaseProvider(Provider):
    scope = Scope.REQUEST

    generate_quiz = provide(GenerateQuizUseCase)
    generate_material_post = provide(GenerateMaterialPostUseCase)