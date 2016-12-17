#!/usr/bin/env python3

import random

from litex.gen import *

from litex.soc.interconnect.stream import *

from litedram.common import LiteDRAMWritePort, LiteDRAMReadPort
from litedram.frontend.bist import LiteDRAMBISTGenerator
from litedram.frontend.bist import LiteDRAMBISTChecker

from test.common import *

class TB(Module):
    def __init__(self):
        self.write_port = LiteDRAMWritePort(aw=32, dw=32)
        self.read_port = LiteDRAMReadPort(aw=32, dw=32)
        self.submodules.generator = LiteDRAMBISTGenerator(self.write_port, random=True)
        self.submodules.checker = LiteDRAMBISTChecker(self.read_port, random=True)


finished = []

def cycle_assert(dut):
    while not finished:
        addr = yield dut.checker.core._address_counter
        data = yield dut.checker.core._data_counter
        assert addr >= data, "addr {} >= data {}".format(addr, data)
        yield


def main_generator(dut, mem):
    # Populate memory with random data
    random.seed(0)
    for i in range(0, len(mem.mem)):
        mem.mem[i] = random.randint(0, 2**mem.width)

    # write
    yield from reset_bist_module(dut.generator)

    yield dut.generator.base.storage.eq(16)
    yield dut.generator.length.storage.eq(64)
    for i in range(8):
        yield
    yield dut.generator.start.re.eq(1)
    yield
    yield dut.generator.start.re.eq(0)
    for i in range(8):
        yield
    while((yield dut.generator.done.status) == 0):
        yield
    done = yield dut.generator.done.status
    assert done, done

    # read with no errors
    yield from reset_bist_module(dut.checker)
    errors = yield dut.checker.err_count.status
    assert errors == 0, errors

    yield dut.checker.base.storage.eq(16)
    yield dut.checker.length.storage.eq(64)
    for i in range(8):
        yield
    yield from toggle_re(dut.checker.start)
    for i in range(8):
        yield
    while((yield dut.checker.done.status) == 0):
        yield
    done = yield dut.checker.done.status
    assert done, done
    errors = yield dut.checker.err_count.status
    assert errors == 0, errors

    yield
    yield

    # read with one error
    yield from reset_bist_module(dut.checker)
    errors = yield dut.checker.err_count.status
    assert errors == 0, errors

    print("mem.mem[20]", hex(mem.mem[20]))
    assert mem.mem[20] == 0xffff000f, hex(mem.mem[20])
    mem.mem[20] = 0x200  # Make position 20 an error

    yield dut.checker.base.storage.eq(16)
    yield dut.checker.length.storage.eq(64)
    for i in range(8):
        yield
    yield from toggle_re(dut.checker.start)
    for i in range(8):
        yield
    while((yield dut.checker.done.status) == 0):
        yield
    done = yield dut.checker.done.status
    assert done, done
    errors = yield dut.checker.err_count.status
    assert errors == 1, errors

    err_addr = yield dut.checker.err_addr.status
    assert err_addr == 20, err_addr

    yield
    yield

    # read with two errors
    yield from reset_bist_module(dut.checker)
    errors = yield dut.checker.err_count.status
    assert errors == 0, errors

    print("mem.mem[21]", hex(mem.mem[21]))
    assert mem.mem[21] == 0xfff1ff1f, hex(mem.mem[21])
    mem.mem[21] = 0x210 # Make position 21 an error

    yield dut.checker.base.storage.eq(16)
    yield dut.checker.length.storage.eq(64)
    for i in range(8):
        yield
    yield from toggle_re(dut.checker.start)
    for i in range(8):
        yield
    while((yield dut.checker.done.status) == 0):
        yield
    done = yield dut.checker.done.status
    assert done, done
    errors = yield dut.checker.err_count.status
    assert errors == 2, errors

    err_addr = yield dut.checker.err_addr.status
    assert err_addr == 21, err_addr

    yield
    yield

    # read with two errors but halting on the first one
    yield from reset_bist_module(dut.checker)
    errors = yield dut.checker.err_count.status
    assert errors == 0, errors

    yield dut.checker.base.storage.eq(16)
    yield dut.checker.length.storage.eq(64)
    yield dut.checker.halt_on_error.storage.eq(1)
    for i in range(8):
        yield
    yield from toggle_re(dut.checker.start)
    for i in range(8):
        yield
    while((yield dut.checker.done.status) == 0):
        yield
    done = yield dut.checker.done.status
    assert done, done
    running = yield dut.checker.core.running
    assert not running, running
    for i in range(16):
        yield

    errors = yield dut.checker.err_count.status
    assert errors == 1, errors
    err_addr = yield dut.checker.err_addr.status
    assert err_addr == 20, err_addr
    err_expect = yield dut.checker.core.err_expect
    assert err_expect == 0xffff000f, err_expect
    err_actual = yield dut.checker.core.err_actual
    assert err_actual == 0x200, err_actual

    yield from toggle_re(dut.checker.start)
    for i in range(8):
        yield
    while((yield dut.checker.done.status) == 0):
        yield
    done = yield dut.checker.done.status
    assert done, done
    running = yield dut.checker.core.running
    assert not running, running
    for i in range(16):
        yield

    errors = yield dut.checker.err_count.status
    assert errors == 2, errors
    err_addr = yield dut.checker.err_addr.status
    assert err_addr == 21, err_addr
    err_expect = yield dut.checker.core.err_expect
    assert err_expect == 0xfff1ff1f, err_expect
    err_actual = yield dut.checker.core.err_actual
    assert err_actual == 0x210, err_actual

    yield from toggle_re(dut.checker.start)
    for i in range(8):
        yield
    while((yield dut.checker.done.status) == 0):
        yield
    done = yield dut.checker.done.status
    assert done, done
    running = yield dut.checker.core.running
    assert running, running
    for i in range(16):
        yield

    err_addr = yield dut.checker.err_addr.status
    err_expect = yield dut.checker.core.err_expect
    err_actual = yield dut.checker.core.err_actual
    errors = yield dut.checker.err_count.status
    assert errors == 2, errors
    err_addr = yield dut.checker.err_addr.status
    assert err_addr == 0, err_addr

    yield
    yield

    finished.append(True)


if __name__ == "__main__":
    tb = TB()
    mem = DRAMMemory(32, 128)
    generators = {
        "sys" : [
            main_generator(tb, mem),
            mem.write_generator(tb.write_port),
            mem.read_generator(tb.read_port),
            cycle_assert(tb),
        ],
    }
    clocks = {"sys": 10}
    run_simulation(tb, generators, clocks, vcd_name="sim.vcd")
