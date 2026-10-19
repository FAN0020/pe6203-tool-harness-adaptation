"""Provider-specific request settings, without reading or storing credentials."""

from urllib.parse import urlparse

OPENROUTER_FLASH = "deepseek/deepseek-v4.1-flash-1017"


def model_id(model, base_url):
    if urlparse(str(base_url)).hostname == "openrouter.ai" and model == "deepseek-flash":
        return OPENROUTER_FLASH
    return model


def nonthinking_options(base_url):
    if urlparse(str(base_url)).hostname == "openrouter.ai":
        return {"reasoning": {"enabled": False}}
    return {"thinking": {"type": "disabled"}}
