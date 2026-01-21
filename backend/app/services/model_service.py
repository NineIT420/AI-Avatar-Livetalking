from config.settings import settings

model = None
avatar = None


def load_model():
    global model

    from ..models.musereal import load_model as load_muse_model
    model = load_muse_model()

    return model


def load_avatar():
    global avatar

    from ..models.musereal import load_avatar as load_muse_avatar
    avatar = load_muse_avatar(settings.avatar_id)  

    return avatar

def warm_up(batch_size: int):
    from ..models.musereal import warm_up as muse_warm_up
    muse_warm_up(batch_size, model)
