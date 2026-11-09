`timescale 1 ns / 1 ps

module tb_mult_16_bit_v1_0();

localparam AXI_CLK_PERIOD = 20; // 20 ns -> 50 MHz

parameter integer C_S00_AXI_DATA_WIDTH	= 32;
parameter integer C_S00_AXI_ADDR_WIDTH	= 6;

// Register Map
localparam A_REG_ADDR    = 32'h0000_0000; // slv_reg0: Operand A [15:0]
localparam B_REG_ADDR    = 32'h0000_0004; // slv_reg1: Operand B [15:0]
localparam PROD_REG_ADDR = 32'h0000_0008; // slv_reg2: Product [31:0] (read-only)
localparam CTRL_REG_ADDR = 32'h0000_000C; // slv_reg3: Control, Bit 0 = CLEAR (write-only, self-clearing)

reg                                 s00_axi_aclk;
reg                                 s00_axi_aresetn;
reg [C_S00_AXI_ADDR_WIDTH-1:0]      s00_axi_awaddr;
reg [2:0]                           s00_axi_awprot;
reg                                 s00_axi_awvalid;
wire                                s00_axi_awready;
reg [C_S00_AXI_DATA_WIDTH-1:0]      s00_axi_wdata;
reg [(C_S00_AXI_DATA_WIDTH/8)-1:0]  s00_axi_wstrb;
reg                                 s00_axi_wvalid;
wire                                s00_axi_wready;
wire [1:0]                          s00_axi_bresp;
wire                                s00_axi_bvalid;
reg                                 s00_axi_bready;
reg [C_S00_AXI_ADDR_WIDTH-1:0]      s00_axi_araddr;
reg [2:0]                           s00_axi_arprot;
reg                                 s00_axi_arvalid;
wire                                s00_axi_arready;
wire [C_S00_AXI_DATA_WIDTH-1:0]     s00_axi_rdata;
wire [1:0]                          s00_axi_rresp;
wire                                s00_axi_rvalid;
reg                                 s00_axi_rready;

mult_16_bit_v1_0 UUT_mult_16_bit_v1_0
(
    .s00_axi_aclk(s00_axi_aclk),
    .s00_axi_aresetn(s00_axi_aresetn),
    .s00_axi_awaddr(s00_axi_awaddr),
    .s00_axi_awprot(s00_axi_awprot),
    .s00_axi_awvalid(s00_axi_awvalid),
    .s00_axi_awready(s00_axi_awready),
    .s00_axi_wdata(s00_axi_wdata),
    .s00_axi_wstrb(s00_axi_wstrb),
    .s00_axi_wvalid(s00_axi_wvalid),
    .s00_axi_wready(s00_axi_wready),
    .s00_axi_bresp(s00_axi_bresp),
    .s00_axi_bvalid(s00_axi_bvalid),
    .s00_axi_bready(s00_axi_bready),
    .s00_axi_araddr(s00_axi_araddr),
    .s00_axi_arprot(s00_axi_arprot),
    .s00_axi_arvalid(s00_axi_arvalid),
    .s00_axi_arready(s00_axi_arready),
    .s00_axi_rdata(s00_axi_rdata),
    .s00_axi_rresp(s00_axi_rresp),
    .s00_axi_rvalid(s00_axi_rvalid),
    .s00_axi_rready(s00_axi_rready)
);

initial begin
    s00_axi_aclk = 1'b0;
    forever #(AXI_CLK_PERIOD / 2) s00_axi_aclk = ~s00_axi_aclk;
end

initial begin
    s00_axi_aresetn = 1'b0;
    repeat (5) @(posedge s00_axi_aclk);

    s00_axi_aresetn = 1'b1;
    @(posedge s00_axi_aclk);
end

initial begin
    s00_axi_awaddr = 0;

    s00_axi_bready = 0;

    s00_axi_wvalid = 0;
    s00_axi_awvalid = 0;
    s00_axi_awprot = 0;
    s00_axi_arvalid = 0;
    s00_axi_wdata = 0;
    s00_axi_wstrb = 4'hF;
    s00_axi_rready = 0;
    s00_axi_araddr = 0;
    s00_axi_arprot = 0;

    repeat (10) @(posedge s00_axi_aclk);

    // Test Case 1: Reading FPGA_VER register
    axi_read(32'h0000_0000);

    // Test 1: 3 x 4 = 12 (0x0000_000C)
    axi_write(A_REG_ADDR, 32'h0000_0003);
    axi_write(B_REG_ADDR, 32'h0000_0004);
    axi_read(PROD_REG_ADDR);

    // Test 2: 0x1234 x 0x0010 = 0x0001_2340
    axi_write(A_REG_ADDR, 32'h0000_1234);
    axi_write(B_REG_ADDR, 32'h0000_0010);
    axi_read(PROD_REG_ADDR);

    // Test 3: 0xFFFF x 0xFFFF = 0xFFFE_0001 (maximum product)
    axi_write(A_REG_ADDR, 32'h0000_FFFF);
    axi_write(B_REG_ADDR, 32'h0000_FFFF);
    axi_read(PROD_REG_ADDR);

    // Test 4: Write to the read-only Product register (should be ignored)
    axi_write(PROD_REG_ADDR, 32'hDEAD_BEEF);
    axi_read(PROD_REG_ADDR);

    // Test 5: Read back the operand registers
    axi_read(A_REG_ADDR);
    axi_read(B_REG_ADDR);

    // Test 6: Set CLEAR (bit 0) in the Control register
    // CLEAR clears operands A and B, so the product becomes 0.
    // The Control register is write-only and self-clears, so it reads back as 0.
    axi_write(CTRL_REG_ADDR, 32'h0000_0001);
    axi_read(CTRL_REG_ADDR);
    axi_read(A_REG_ADDR);
    axi_read(B_REG_ADDR);
    axi_read(PROD_REG_ADDR);

    // Test 7: The multiplier still works after CLEAR: 5 x 6 = 30 (0x0000_001E)
    axi_write(A_REG_ADDR, 32'h0000_0005);
    axi_write(B_REG_ADDR, 32'h0000_0006);
    axi_read(PROD_REG_ADDR);

    repeat (10) @(posedge s00_axi_aclk);
    // $finish;
end

// Show how long the CLEAR bit stays high (it should be exactly one clock cycle)
always @(posedge s00_axi_aclk) begin
    if (UUT_mult_16_bit_v1_0.mult_16_bit_v1_0_S00_AXI_inst.slv_reg3[0])
        $display ("[%g] CLEAR bit is high", $time);
end

task axi_write;
    input [31:0] reg_addr;
    input [31:0] reg_data;
begin
    s00_axi_awprot = 3'b000;
    s00_axi_wstrb = 4'hF;
    s00_axi_bready = 1'b0;

    @(posedge s00_axi_aclk);
    s00_axi_awaddr = reg_addr;
    s00_axi_awvalid = 1'b1;

    s00_axi_wdata = reg_data;
    s00_axi_wvalid = 1'b1;
    s00_axi_bready = 1;

    while (!(s00_axi_awready && s00_axi_wready))
        @(posedge s00_axi_aclk);

    @(posedge s00_axi_aclk);
    s00_axi_awvalid = 1'b0;
    s00_axi_wvalid = 1'b0;

    while (!s00_axi_bvalid)
        @(posedge s00_axi_aclk);

    @(posedge s00_axi_aclk);
    s00_axi_bready = 1'b0;

    $display ("[%g] AXI_WRITE Addr: 0x%08h | Value: 0x%08h", $time, reg_addr, reg_data);
end
endtask

task axi_read;
    input [31:0] reg_addr;
    reg [31:0] reg_value;
begin

    s00_axi_arprot = 3'b000;
    s00_axi_rready = 1'b0;

    @(posedge s00_axi_aclk);
    s00_axi_araddr = reg_addr;
    s00_axi_arvalid = 1'b1;

    while (!s00_axi_arready)
        @(posedge s00_axi_aclk);

    @(posedge s00_axi_aclk);
    s00_axi_arvalid = 1'b0;

    s00_axi_rready = 1'b1;

    while (!s00_axi_rvalid)
        @(posedge s00_axi_aclk);
    reg_value = s00_axi_rdata;

    @(posedge s00_axi_aclk);
    s00_axi_rready = 1'b0;

    $display ("[%g] AXI_READ Addr: 0x%08h | Value: 0x%08h", $time, reg_addr, reg_value);
end
endtask

endmodule
