`timescale 1ns / 1ps

module tb_multiplier_16_bit();

parameter integer CLK_PERIOD = 8;

reg clk;
reg rst_n;
reg [15:0] a;
reg [15:0] b;
wire [31:0] prod;

integer i;

multiplier_16_bit UUT_multiplier_16_bit
(
    .clk(clk),
    .rst_n(rst_n),
    .a(a),
    .b(b),
    .prod(prod)
);

initial begin
    clk = 1'b0;
    forever #(CLK_PERIOD / 2) clk = ~clk;
end

initial begin
    rst_n = 1'b0;
    repeat (5) @(posedge clk);
    
    rst_n = 1'b1;
    @(posedge clk);
end

initial begin
    a = 0;
    b = 0;
    repeat (10) @(posedge clk);
    
    for (i = 0; i < 32; i = i + 1) begin
        a = i;
        b = i;
        @(posedge clk);
    end
    
    a = 0;
    b = 0;
    @(posedge clk);
end

endmodule
