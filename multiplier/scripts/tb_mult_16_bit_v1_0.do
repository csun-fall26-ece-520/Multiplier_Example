quit -sim

# RTL
vlog ../rtl/multiplier_16_bit.v
vlog ../rtl/mult_16_bit_v1_0_S00_AXI.v
vlog ../rtl/mult_16_bit_v1_0.v

# Testbench
vlog ../tests/tb_mult_16_bit_v1_0.v

vsim -voptargs="+acc" work.tb_mult_16_bit_v1_0

add wave -divider -height 30 {AXI-Lite Multiplier}
add wave sim:/tb_mult_16_bit_v1_0/UUT_mult_16_bit_v1_0/mult_16_bit_v1_0_S00_AXI_inst/*

add wave -divider -height 30 {16-Bit Multiplier}
add wave sim:/tb_mult_16_bit_v1_0/UUT_mult_16_bit_v1_0/mult_16_bit_v1_0_S00_AXI_inst/multiplier_16_bit_inst_/*

run 5us
