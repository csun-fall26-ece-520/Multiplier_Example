quit -sim

# RTL
vlog ../rtl/multiplier_16_bit.v

# Testbench
vlog ../tests/tb_multiplier_16_bit.v

vsim -voptargs="+acc" work.tb_multiplier_16_bit

add wave -divider -height 30 {16-Bit Multiplier}
add wave sim:/tb_multiplier_16_bit/UUT_multiplier_16_bit/*

run 5us
