from app.helpers.context import MockLambdaContext, MockLambdaEvent


def test_main_returns_success_response():
    from handlers.inference import main

    event = MockLambdaEvent()
    context = MockLambdaContext()

    result = main(event, context)

    assert result == {"statusCode": 200, "body": "Hello Spartan!"}


def test_module_entrypoint_runs_without_raising():
    import runpy

    runpy.run_module("handlers.inference", run_name="__main__")


def test_module_entrypoint_logs_unhandled_exception(monkeypatch):
    import runpy

    exception_calls = []

    class FakeLogger:
        def info(self, *args, **kwargs):
            raise RuntimeError("boom-info")

        def debug(self, *args, **kwargs):
            pass

        def warning(self, *args, **kwargs):
            pass

        def error(self, *args, **kwargs):
            pass

        def exception(self, *args, **kwargs):
            exception_calls.append((args, kwargs))

    monkeypatch.setattr("app.helpers.logger.get_logger", lambda name=None: FakeLogger())

    runpy.run_module("handlers.inference", run_name="__main__")

    assert exception_calls
    assert "Unhandled exception in main" in exception_calls[0][0][0]
