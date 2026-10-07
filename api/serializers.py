from models.device import Device


def device_serializer(device: Device) -> dict:
    return {
        "id_device": device.id_device,
        "name": device.name,
        "description": device.description,
        "status": device.status,
        "image_url": device.image_url,
        "video_url": device.video_url,
        "power": device.power,
        "resistance": device.resistance,
        "date_created": device.date_created,
        "id_user": device.id_user,
    }
