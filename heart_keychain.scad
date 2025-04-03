// Heart Keychain Model
// Created on April 2, 2025

// Parameters for customization
heart_width = 40;
heart_height = 35;
heart_thickness = 5;
// Keychain loop parameters
loop_diameter = 6; // Slightly larger for better strength
loop_thickness = heart_thickness;
loop_position = [0, -heart_height + 3, 0]; // Modified to connect at the bottom point of the heart
// Key hole parameters
key_hole_width = 8;
key_hole_height = 12;
key_hole_position = [0, heart_height/2 - 10, 0]; // Moved lower to avoid conflict with loop

// Module to create a 2D heart shape
module heart_2d(width, height) {
    union() {
        // Left half of the heart
        translate([-width/4, 0, 0])
        circle(d = width/2, $fn=50);
        
        // Right half of the heart
        translate([width/4, 0, 0])
        circle(d = width/2, $fn=50);
        
        // Bottom triangle part of the heart
        polygon(points=[
            [-width/2, 0],
            [width/2, 0],
            [0, -height]
        ]);
    }
}

// Keychain loop module - improved to ensure no artifacts
module keychain_loop(diameter, thickness) {
    difference() {
        // Outer circle of the loop
        rotate_extrude(angle = 360, $fn=40)
        translate([diameter/2, 0, 0])
        circle(d = thickness, $fn=20);
        
        // No internal subtractions needed - keeping it clean and simple
    }
}

// Key hole module
module key_hole(width, height, thickness) {
    // Classic keyhole shape
    union() {
        // Circular top part
        translate([0, height/3, 0])
        cylinder(h = thickness + 1, d = width, center = true, $fn=30);
        
        // Rectangular bottom part
        translate([0, -height/4, 0])
        cube([width/2, height/1.5, thickness + 1], center = true);
    }
}

// Main heart with keychain loop
module heart_keychain() {
    union() {
        difference() {
            // Heart base (extrude the 2D heart)
            linear_extrude(height = heart_thickness, center = true)
            heart_2d(heart_width, heart_height);
            
            // Subtract key hole
            translate(key_hole_position)
            key_hole(key_hole_width, key_hole_height, heart_thickness);
        }
        
        // Add the keychain loop with proper connection to heart
        translate(loop_position) {
            // Connection bridge to ensure the loop connects to the heart
            translate([0, loop_diameter/2, 0])
            cube([loop_diameter/2, loop_diameter/2, heart_thickness], center = true);
            
            // The loop itself
            keychain_loop(loop_diameter, loop_thickness);
        }
    }
}

// Render the model
heart_keychain();

// Uncomment to check just the 2D heart profile
// heart_2d(heart_width, heart_height);