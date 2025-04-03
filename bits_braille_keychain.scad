// Braille Keychain with "bits" text
// Created on April 2, 2025

// Keychain base parameters
base_width = 50;
base_height = 20;
base_thickness = 4;
corner_radius = 3;

// Braille dot parameters
dot_diameter = 1.8;
dot_height = 1;
dot_spacing_x = 2.5;  // Horizontal spacing between dots in same character
dot_spacing_y = 2.5;  // Vertical spacing between dots in same character
char_spacing = 6;     // Spacing between characters

// Keychain loop parameters
loop_outer_diameter = 8;  // Outer diameter of the keyloop
loop_inner_diameter = 5;  // Inner diameter of the keyloop (hole)
loop_offset = 5;          // Distance from the edge

// Braille patterns for "bits"
// Braille uses 2×3 grid of dots, numbered:
// 1 4
// 2 5
// 3 6
//
// b: dots 1,2
// i: dots 2,4
// t: dots 2,3,4,5
// s: dots 2,3,4

// Module to create rounded rectangle base for keychain
module rounded_rectangle(width, height, radius, thickness) {
    linear_extrude(height = thickness) {
        hull() {
            translate([radius, radius, 0])
                circle(r = radius, $fn = 30);
            
            translate([width - radius, radius, 0])
                circle(r = radius, $fn = 30);
            
            translate([radius, height - radius, 0])
                circle(r = radius, $fn = 30);
            
            translate([width - radius, height - radius, 0])
                circle(r = radius, $fn = 30);
        }
    }
}

// Module to create a single braille dot
module braille_dot() {
    cylinder(h = dot_height, d = dot_diameter, $fn = 20);
}

// Module to create a braille character based on dot pattern
module braille_char(dots) {
    for (i = [0 : len(dots) - 1]) {
        dot = dots[i];
        
        // Calculate position based on dot number (1-6)
        x = (dot == 4 || dot == 5 || dot == 6) ? dot_spacing_x : 0;
        y = (dot == 1 || dot == 4) ? dot_spacing_y * 2 : 
            ((dot == 2 || dot == 5) ? dot_spacing_y : 0);
            
        translate([x, y, 0])
            braille_dot();
    }
}

// Module to create the keychain loop
module keychain_loop() {
    difference() {
        // Outer cylinder for the loop
        cylinder(h = base_thickness, d = loop_outer_diameter, $fn = 30);
        
        // Inner cylinder to create the hole - ensure it goes through completely
        translate([0, 0, -1])
            cylinder(h = base_thickness + 2, d = loop_inner_diameter, $fn = 30);
    }
}

// Main module to create the entire keychain
module braille_keychain() {
    // Create the base with the loop as a single solid piece
    union() {
        // Base plate with rounded corners
        rounded_rectangle(base_width, base_height, corner_radius, base_thickness);
        
        // Add keychain loop - ensure it connects properly to the base
        translate([base_width - loop_offset - loop_outer_diameter/2, base_height/2, 0])
            keychain_loop();
    }
    
    // Create the hole for the keychain loop as a separate operation to ensure it's visible
    translate([base_width - loop_offset - loop_outer_diameter/2, base_height/2, -1])
        cylinder(h = base_thickness + 2, d = loop_inner_diameter, $fn = 30);
    
    // Starting position for the first character
    start_x = 10;
    start_y = base_height/2 - dot_spacing_y;
    
    // Add braille characters for "bits"
    // b: dots 1,2
    translate([start_x, start_y, base_thickness])
        braille_char([1, 2]);
    
    // i: dots 2,4
    translate([start_x + char_spacing, start_y, base_thickness])
        braille_char([2, 4]);
    
    // t: dots 2,3,4,5
    translate([start_x + char_spacing*2, start_y, base_thickness])
        braille_char([2, 3, 4, 5]);
    
    // s: dots 2,3,4
    translate([start_x + char_spacing*3, start_y, base_thickness])
        braille_char([2, 3, 4]);
}

// Render the keychain
braille_keychain();