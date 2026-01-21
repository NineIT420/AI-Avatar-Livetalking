from config.settings import settings
from ..utils.logger import logger

model = None
avatar = None


def load_model():
    global model

    if settings.model == 'musetalk':
        from ..models.musereal import load_model as load_muse_model
        logger.info("Loading MuseTalk model...")
        model = load_muse_model()
    elif settings.model == 'wav2lip':
        logger.info("Loading Wav2Lip model...")
        model = load_wav2lip_model()
    elif settings.model == 'ultralight':
        logger.info("Loading UltraLight model...")
        model = load_ultralight_model()
    else:
        raise ValueError(f"Unknown model type: {settings.model}")

    return model


def load_wav2lip_model():
    return None


def load_ultralight_model():
    return None


def load_avatar():
    global avatar

    if settings.model == 'musetalk':
        from ..models.musereal import load_avatar as load_muse_avatar
        logger.info(f"Loading avatar: {settings.avatar_id}")
        avatar = load_muse_avatar(settings.avatar_id)
    elif settings.model == 'wav2lip':
        avatar = load_wav2lip_avatar()
    elif settings.model == 'ultralight':
        avatar = load_ultralight_avatar()

    return avatar


def load_wav2lip_avatar():
    return None


def load_ultralight_avatar():
    return None


def warm_up(batch_size: int):
    if settings.model == 'musetalk':
        from ..models.musereal import warm_up as muse_warm_up
        logger.info("Warming up MuseTalk model...")
        muse_warm_up(batch_size, model)
    elif settings.model == 'wav2lip':
        warm_up_wav2lip(batch_size)
    elif settings.model == 'ultralight':
        warm_up_ultralight(batch_size)


def warm_up_wav2lip(batch_size: int):
    pass


def warm_up_ultralight(batch_size: int):
    pass
