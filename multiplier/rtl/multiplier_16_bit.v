`timescale 1ns / 1ps

module multiplier_16_bit
(
    input clk,
    input rst_n,
    input [15:0] a,
    input [15:0] b,
    output reg [31:0] prod
);

always @(posedge clk) begin
    if (!rst_n) begin
        prod <= 0;
    end else begin
        prod <= a * b;
    end
end

endmodule
