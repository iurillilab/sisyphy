function velocity = movePointer(vr)
fwrite(vr.client, "read_velocities")
vels = fread(vr.client, 2) - 127;

velocity = [0 0 0 0];
ptr = [vels(2) -vels(1)]
velocity(1) = ptr(2)/2*sin(-vr.position(4));
velocity(2) = ptr(2)/2*cos(-vr.position(4));
velocity(4) = ptr(1)/20;