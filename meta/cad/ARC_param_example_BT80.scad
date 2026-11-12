// ARC-class parametric model rocket - OpenSCAD source
// Units: mm. Derived example for American Rocketry Challenge 2027 class (800 ft, 2x egg, 37-40 s)
// Source: GENERATED parametric example (CC0), dimensions based on Estes BT-80 (66mm OD) + ARC 2027 rules.
// See ../SOURCES.md. Not an official ARC kit. Verify stability in OpenRocket before building.
// Open in OpenSCAD, export to STL if needed. Fits 24/29mm motors with adapter.

BT_OD = 66; BT_ID = 63; BT_LEN = 460;
NOSE_LEN = 130; NOSE_SHOULDER = 30;
FIN_ROOT = 140; FIN_TIP = 60; FIN_SPAN = 110; FIN_THICK = 3.2;
MOTOR_DIA = 24; RING_THICK = 5;

module ogive_nose(R=BT_OD/2, L=NOSE_LEN) {
  // approximate tangent ogive via rotated polygon
  pts = [for (i=[0:16]) let(t=i/16, r=R*sqrt(1-pow(1-t,2))) [r, t*L]];
  rotate_extrude($fn=64) polygon(concat([[0,0]], pts, [[0,L]]));
}
module body_tube() {
  difference() {
    cylinder(d=BT_OD, h=BT_LEN, $fn=64);
    translate([0,0,-1]) cylinder(d=BT_ID, h=BT_LEN+2, $fn=64);
  }
}
module fin_2d() {
  polygon([[0,0],[FIN_ROOT,0],[110,FIN_SPAN],[40,FIN_SPAN]]);
}
module fin_3d() {
  linear_extrude(FIN_THICK) fin_2d();
}
module centering_ring(od=BT_ID, id=MOTOR_DIA+1) {
  difference() {
    cylinder(d=od, h=RING_THICK, $fn=64);
    translate([0,0,-1]) cylinder(d=id, h=RING_THICK+2, $fn=48);
  }
}
// Assembly preview:
translate([0,0,BT_LEN]) ogive_nose();
body_tube();
for (a=[0:120:359]) rotate([0,0,a]) translate([BT_OD/2-1, -FIN_THICK/2, 20]) fin_3d();
translate([0,0,40]) centering_ring();
translate([0,0,BT_LEN-140]) centering_ring();
// Egg capsule zone (2x Grade A Large, 55-63g each, ~44x58mm): reserve 130mm
// Motor mount tube 24mm x 95mm (E12 size)
%translate([0,0,-80]) cylinder(d=MOTOR_DIA, h=95, $fn=32);
