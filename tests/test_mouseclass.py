from sisyphy.sphere_velocity.hardware.usbmouse_reader import DummyMouse
from sisyphy.sphere_velocity.sphere_dataclasses import MouseVelocityData


def test_mouseclass():
    dummy_mouse = DummyMouse()

    vel = dummy_mouse.get_velocities()

    assert isinstance(vel, MouseVelocityData)

    assert isinstance(vel.x, float)
    assert isinstance(vel.y, float)
