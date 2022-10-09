from sisyphy.hardware.usbmouse import DummyMouse
from sisyphy.custom_dataclasses import MouseVelocityData


def test_mouseclass():
    dummy_mouse = DummyMouse()

    vel = dummy_mouse.get_velocities()

    assert isinstance(vel, MouseVelocityData)

    assert isinstance(vel.x, float)
    assert isinstance(vel.y, float)
