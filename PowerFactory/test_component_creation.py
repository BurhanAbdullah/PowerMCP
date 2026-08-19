import unittest

import Agent_DIgSILENT as agent_module


class FakeGeneratorType:
    def __init__(self, name):
        self.name = name

    def GetFullName(self):
        return rf"\user\Library\{self.name}.TypSym"


class FakeCubicle:
    def __init__(self, parent, name):
        self.parent = parent
        self.attributes = {"loc_name": name}

    def GetAttribute(self, name):
        return self.attributes[name]

    def GetFullName(self):
        return (
            f"{self.parent.GetFullName()}\\"
            f"{self.attributes['loc_name']}.StaCubic"
        )

    def Delete(self):
        self.parent.cubicles.remove(self)


class FakeLineType:
    def __init__(self, name):
        self.name = name

    def GetFullName(self):
        return rf"\user\Library\{self.name}.TypLne"


class FakeTransformerType:
    def __init__(self, name):
        self.name = name

    def GetFullName(self):
        return rf"\user\Library\{self.name}.TypTr2"


class FakeBus:
    def __init__(self, parent, name):
        self.parent = parent
        self.cubicles = []
        self.attributes = {
            "loc_name": name,
            "uknom": 0.0,
            "outserv": 0,
        }

    def GetAttribute(self, name):
        return self.attributes[name]

    def SetAttribute(self, name, value):
        if name == "uknom" and self.parent.reject_voltage:
            return
        self.attributes[name] = value

    def GetFullName(self):
        return (
            rf"\user\test.IntPrj\Grid\{self.attributes['loc_name']}.ElmTerm"
        )

    def GetContents(self, query, recursive):
        if query == "*.StaCubic":
            return list(self.cubicles)
        return []

    def CreateObject(self, class_name, name):
        if class_name != "StaCubic":
            return None
        cubicle = FakeCubicle(self, name)
        self.cubicles.append(cubicle)
        return cubicle

    def Delete(self):
        self.parent.terminals.remove(self)


class FakeLoad:
    def __init__(self, parent, name):
        self.parent = parent
        self.attributes = {
            "loc_name": name,
            "bus1": None,
            "plini": 0.0,
            "qlini": 0.0,
            "outserv": 0,
        }

    def GetAttribute(self, name):
        return self.attributes[name]

    def SetAttribute(self, name, value):
        if name == "plini" and self.parent.reject_load_power:
            return
        self.attributes[name] = value

    def GetFullName(self):
        return (
            rf"\user\test.IntPrj\Grid\{self.attributes['loc_name']}.ElmLod"
        )

    def Delete(self):
        self.parent.loads.remove(self)


class FakeGenerator:
    def __init__(self, parent, name):
        self.parent = parent
        self.attributes = {
            "loc_name": name,
            "typ_id": None,
            "bus1": None,
            "pgini": 0.0,
            "qgini": 0.0,
            "outserv": 0,
        }

    def GetAttribute(self, name):
        return self.attributes[name]

    def SetAttribute(self, name, value):
        if name == "pgini" and self.parent.reject_generator_power:
            return
        self.attributes[name] = value

    def GetClassName(self):
        return "ElmSym"

    def GetFullName(self):
        return (
            rf"\user\test.IntPrj\Grid\{self.attributes['loc_name']}.ElmSym"
        )

    def Delete(self):
        self.parent.generators.remove(self)


class FakeLine:
    def __init__(self, parent, name):
        self.parent = parent
        self.attributes = {
            "loc_name": name,
            "typ_id": None,
            "bus1": None,
            "bus2": None,
            "dline": 0.0,
            "outserv": 0,
        }

    def GetAttribute(self, name):
        return self.attributes[name]

    def SetAttribute(self, name, value):
        if name == "dline" and self.parent.reject_line_length:
            return
        self.attributes[name] = value

    def GetClassName(self):
        return "ElmLne"

    def GetFullName(self):
        return (
            rf"\user\test.IntPrj\Grid\{self.attributes['loc_name']}.ElmLne"
        )

    def Delete(self):
        self.parent.lines.remove(self)


class FakeTransformer:
    def __init__(self, parent, name):
        self.parent = parent
        self.attributes = {
            "loc_name": name,
            "typ_id": None,
            "bushv": None,
            "buslv": None,
            "outserv": 0,
        }

    def GetAttribute(self, name):
        return self.attributes[name]

    def SetAttribute(self, name, value):
        if name == "typ_id" and self.parent.reject_transformer_type:
            return
        self.attributes[name] = value

    def GetClassName(self):
        return "ElmTr2"

    def GetFullName(self):
        return (
            rf"\user\test.IntPrj\Grid\{self.attributes['loc_name']}.ElmTr2"
        )

    def Delete(self):
        self.parent.transformers.remove(self)


class FakeGrid:
    def __init__(
        self,
        name,
        reject_voltage=False,
        reject_load_power=False,
        reject_generator_power=False,
        reject_line_length=False,
        reject_transformer_type=False,
    ):
        self.name = name
        self.reject_voltage = reject_voltage
        self.reject_load_power = reject_load_power
        self.reject_generator_power = reject_generator_power
        self.reject_line_length = reject_line_length
        self.reject_transformer_type = reject_transformer_type
        self.terminals = []
        self.loads = []
        self.generators = []
        self.lines = []
        self.transformers = []

    def GetAttribute(self, name):
        if name == "loc_name":
            return self.name
        raise KeyError(name)

    def GetContents(self, query, recursive):
        if query == "*.ElmTerm":
            return list(self.terminals)
        if query == "*.ElmLod":
            return list(self.loads)
        if query == "*.ElmSym":
            return list(self.generators)
        if query == "*.ElmLne":
            return list(self.lines)
        if query == "*.ElmTr2":
            return list(self.transformers)
        return []

    def CreateObject(self, class_name, name):
        if class_name == "ElmTerm":
            bus = FakeBus(self, name)
            self.terminals.append(bus)
            return bus

        if class_name == "ElmLod":
            load = FakeLoad(self, name)
            self.loads.append(load)
            return load

        if class_name == "ElmSym":
            generator = FakeGenerator(self, name)
            self.generators.append(generator)
            return generator

        if class_name == "ElmLne":
            line = FakeLine(self, name)
            self.lines.append(line)
            return line

        if class_name == "ElmTr2":
            transformer = FakeTransformer(self, name)
            self.transformers.append(transformer)
            return transformer

        return None


class FakeApplication:
    def __init__(self, grids, objects=None):
        self.grids = grids
        self.objects = objects or {}
        self.shown = None

    def GetCalcRelevantObjects(self, query):
        if query == "*.ElmNet":
            return self.grids
        return list(self.objects.get(query, []))

    def Show(self):
        self.shown = True

    def Hide(self):
        self.shown = False


class FakePowerFactory:
    def __init__(self, app):
        self.app = app

    def GetApplicationExt(self):
        return self.app


class ComponentCreationTest(unittest.TestCase):
    def setUp(self):
        self.original_pf = agent_module.pf
        self.original_app = agent_module.DIgSILENTAgent._shared_app

    def tearDown(self):
        agent_module.pf = self.original_pf
        agent_module.DIgSILENTAgent._shared_app = self.original_app

    def use_application(self, app):
        agent_module.pf = FakePowerFactory(app)
        agent_module.DIgSILENTAgent._shared_app = None

    def test_add_bus_validation_and_rollback(self):
        grid = FakeGrid("Grid")
        self.use_application(FakeApplication([grid]))

        ok, message = agent_module.DIgSILENTAgent.add_bus(
            "MCP Test Bus",
            110.0,
            open_digsilent=False,
        )

        self.assertTrue(ok, message)
        self.assertEqual(len(grid.terminals), 1)
        self.assertEqual(
            grid.terminals[0].GetAttribute("uknom"),
            110.0,
        )
        self.assertEqual(
            grid.terminals[0].GetAttribute("outserv"),
            0,
        )

        ok, message = agent_module.DIgSILENTAgent.add_bus(
            "MCP Test Bus",
            110.0,
            open_digsilent=False,
        )
        self.assertFalse(ok)
        self.assertIn("already exists", message)
        self.assertEqual(len(grid.terminals), 1)

        ok, message = agent_module.DIgSILENTAgent.add_bus(
            "Invalid Bus",
            -1.0,
            open_digsilent=False,
        )
        self.assertFalse(ok)
        self.assertIn("finite positive", message)
        self.assertEqual(len(grid.terminals), 1)

        grid_a = FakeGrid("Grid A")
        grid_b = FakeGrid("Grid B")
        self.use_application(FakeApplication([grid_a, grid_b]))

        ok, message = agent_module.DIgSILENTAgent.add_bus(
            "Ambiguous Bus",
            20.0,
            open_digsilent=False,
        )
        self.assertFalse(ok)
        self.assertIn("Multiple grids", message)

        ok, message = agent_module.DIgSILENTAgent.add_bus(
            "Selected Bus",
            20.0,
            grid_name="Grid B",
            out_of_service=True,
            open_digsilent=False,
        )
        self.assertTrue(ok, message)
        self.assertEqual(len(grid_a.terminals), 0)
        self.assertEqual(len(grid_b.terminals), 1)
        self.assertEqual(
            grid_b.terminals[0].GetAttribute("outserv"),
            1,
        )

        failing_grid = FakeGrid(
            "Grid",
            reject_voltage=True,
        )
        self.use_application(FakeApplication([failing_grid]))

        ok, message = agent_module.DIgSILENTAgent.add_bus(
            "Rollback Bus",
            110.0,
            open_digsilent=False,
        )
        self.assertFalse(ok)
        self.assertIn("rolled_back=True", message)
        self.assertEqual(failing_grid.terminals, [])

    def test_add_load_validation_and_rollback(self):
        grid = FakeGrid("Grid")
        bus = grid.CreateObject("ElmTerm", "Bus 01")
        self.use_application(FakeApplication([grid]))

        ok, message = agent_module.DIgSILENTAgent.add_load(
            "MCP Test Load",
            "Bus 01",
            50.0,
            12.5,
            out_of_service=True,
            open_digsilent=False,
        )

        self.assertTrue(ok, message)
        self.assertEqual(len(grid.loads), 1)
        self.assertEqual(len(bus.cubicles), 1)
        self.assertIs(
            grid.loads[0].GetAttribute("bus1"),
            bus.cubicles[0],
        )
        self.assertEqual(
            grid.loads[0].GetAttribute("plini"),
            50.0,
        )
        self.assertEqual(
            grid.loads[0].GetAttribute("qlini"),
            12.5,
        )
        self.assertEqual(
            grid.loads[0].GetAttribute("outserv"),
            1,
        )

        ok, message = agent_module.DIgSILENTAgent.add_load(
            "MCP Test Load",
            "Bus 01",
            50.0,
            open_digsilent=False,
        )
        self.assertFalse(ok)
        self.assertIn("already exists", message)
        self.assertEqual(len(grid.loads), 1)
        self.assertEqual(len(bus.cubicles), 1)

        ok, message = agent_module.DIgSILENTAgent.add_load(
            "Missing Bus Load",
            "Unknown Bus",
            10.0,
            open_digsilent=False,
        )
        self.assertFalse(ok)
        self.assertIn("Bus not found", message)

        ok, message = agent_module.DIgSILENTAgent.add_load(
            "Invalid Load",
            "Bus 01",
            -1.0,
            open_digsilent=False,
        )
        self.assertFalse(ok)
        self.assertIn("finite and non-negative", message)

        failing_grid = FakeGrid(
            "Grid",
            reject_load_power=True,
        )
        failing_bus = failing_grid.CreateObject(
            "ElmTerm",
            "Bus 01",
        )
        self.use_application(FakeApplication([failing_grid]))

        ok, message = agent_module.DIgSILENTAgent.add_load(
            "Rollback Load",
            "Bus 01",
            10.0,
            open_digsilent=False,
        )

        self.assertFalse(ok)
        self.assertIn("rolled_back=True", message)
        self.assertEqual(failing_grid.loads, [])
        self.assertEqual(failing_bus.cubicles, [])

    def test_add_generator_validation_and_rollback(self):
        grid = FakeGrid("Grid")
        bus = grid.CreateObject("ElmTerm", "Bus 01")
        machine_type = FakeGeneratorType("Test Machine Type")
        template = grid.CreateObject("ElmSym", "G 01")
        template.SetAttribute("typ_id", machine_type)

        self.use_application(FakeApplication(
            [grid],
            {"G 01.ElmSym": [template]},
        ))

        ok, message = agent_module.DIgSILENTAgent.add_generator(
            "MCP Test Generator",
            "Bus 01",
            "G 01.ElmSym",
            25.0,
            5.0,
            out_of_service=True,
            open_digsilent=False,
        )

        self.assertTrue(ok, message)
        self.assertEqual(len(grid.generators), 2)
        self.assertEqual(len(bus.cubicles), 1)

        created = grid.generators[1]
        self.assertIs(
            created.GetAttribute("typ_id"),
            machine_type,
        )
        self.assertIs(
            created.GetAttribute("bus1"),
            bus.cubicles[0],
        )
        self.assertEqual(created.GetAttribute("pgini"), 25.0)
        self.assertEqual(created.GetAttribute("qgini"), 5.0)
        self.assertEqual(created.GetAttribute("outserv"), 1)

        ok, message = agent_module.DIgSILENTAgent.add_generator(
            "MCP Test Generator",
            "Bus 01",
            "G 01.ElmSym",
            25.0,
            open_digsilent=False,
        )
        self.assertFalse(ok)
        self.assertIn("already exists", message)
        self.assertEqual(len(grid.generators), 2)

        ok, message = agent_module.DIgSILENTAgent.add_generator(
            "Missing Template Generator",
            "Bus 01",
            "Unknown.ElmSym",
            10.0,
            open_digsilent=False,
        )
        self.assertFalse(ok)
        self.assertIn("Template generator not found", message)

        failing_grid = FakeGrid(
            "Grid",
            reject_generator_power=True,
        )
        failing_bus = failing_grid.CreateObject(
            "ElmTerm",
            "Bus 01",
        )
        failing_template = failing_grid.CreateObject(
            "ElmSym",
            "G 01",
        )
        failing_template.SetAttribute("typ_id", machine_type)

        self.use_application(FakeApplication(
            [failing_grid],
            {"G 01.ElmSym": [failing_template]},
        ))

        ok, message = agent_module.DIgSILENTAgent.add_generator(
            "Rollback Generator",
            "Bus 01",
            "G 01.ElmSym",
            10.0,
            open_digsilent=False,
        )

        self.assertFalse(ok)
        self.assertIn("rolled_back=True", message)
        self.assertEqual(
            failing_grid.generators,
            [failing_template],
        )
        self.assertEqual(failing_bus.cubicles, [])

    def test_add_line_validation_and_rollback(self):
        grid = FakeGrid("Grid")
        bus_1 = grid.CreateObject("ElmTerm", "Bus 01")
        bus_2 = grid.CreateObject("ElmTerm", "Bus 02")
        line_type = FakeLineType("Test Line Type")
        template = grid.CreateObject("ElmLne", "Line 01 - 02")
        template.SetAttribute("typ_id", line_type)

        self.use_application(FakeApplication(
            [grid],
            {"Line 01 - 02.ElmLne": [template]},
        ))

        ok, message = agent_module.DIgSILENTAgent.add_line(
            "MCP Test Line",
            "Bus 01",
            "Bus 02",
            "Line 01 - 02.ElmLne",
            10.0,
            out_of_service=True,
            open_digsilent=False,
        )

        self.assertTrue(ok, message)
        self.assertEqual(len(grid.lines), 2)
        self.assertEqual(len(bus_1.cubicles), 1)
        self.assertEqual(len(bus_2.cubicles), 1)

        created = grid.lines[1]
        self.assertIs(created.GetAttribute("typ_id"), line_type)
        self.assertIs(
            created.GetAttribute("bus1"),
            bus_1.cubicles[0],
        )
        self.assertIs(
            created.GetAttribute("bus2"),
            bus_2.cubicles[0],
        )
        self.assertEqual(created.GetAttribute("dline"), 10.0)
        self.assertEqual(created.GetAttribute("outserv"), 1)

        ok, message = agent_module.DIgSILENTAgent.add_line(
            "MCP Test Line",
            "Bus 01",
            "Bus 02",
            "Line 01 - 02.ElmLne",
            10.0,
            open_digsilent=False,
        )
        self.assertFalse(ok)
        self.assertIn("already exists", message)
        self.assertEqual(len(grid.lines), 2)

        ok, message = agent_module.DIgSILENTAgent.add_line(
            "Same Bus Line",
            "Bus 01",
            "Bus 01",
            "Line 01 - 02.ElmLne",
            10.0,
            open_digsilent=False,
        )
        self.assertFalse(ok)
        self.assertIn("must be different", message)

        ok, message = agent_module.DIgSILENTAgent.add_line(
            "Missing Template Line",
            "Bus 01",
            "Bus 02",
            "Unknown.ElmLne",
            10.0,
            open_digsilent=False,
        )
        self.assertFalse(ok)
        self.assertIn("Template line not found", message)

        failing_grid = FakeGrid(
            "Grid",
            reject_line_length=True,
        )
        failing_bus_1 = failing_grid.CreateObject(
            "ElmTerm",
            "Bus 01",
        )
        failing_bus_2 = failing_grid.CreateObject(
            "ElmTerm",
            "Bus 02",
        )
        failing_template = failing_grid.CreateObject(
            "ElmLne",
            "Line 01 - 02",
        )
        failing_template.SetAttribute("typ_id", line_type)

        self.use_application(FakeApplication(
            [failing_grid],
            {"Line 01 - 02.ElmLne": [failing_template]},
        ))

        ok, message = agent_module.DIgSILENTAgent.add_line(
            "Rollback Line",
            "Bus 01",
            "Bus 02",
            "Line 01 - 02.ElmLne",
            10.0,
            open_digsilent=False,
        )

        self.assertFalse(ok)
        self.assertIn("rolled_back=True", message)
        self.assertEqual(
            failing_grid.lines,
            [failing_template],
        )
        self.assertEqual(failing_bus_1.cubicles, [])
        self.assertEqual(failing_bus_2.cubicles, [])

    def test_add_transformer_validation_and_rollback(self):
        grid = FakeGrid("Grid")
        high_voltage_bus = grid.CreateObject(
            "ElmTerm",
            "Bus 02",
        )
        low_voltage_bus = grid.CreateObject(
            "ElmTerm",
            "Bus 30",
        )
        transformer_type = FakeTransformerType(
            "Test Transformer Type"
        )
        template = grid.CreateObject(
            "ElmTr2",
            "Trf 02 - 30",
        )
        template.SetAttribute("typ_id", transformer_type)

        self.use_application(FakeApplication(
            [grid],
            {"Trf 02 - 30.ElmTr2": [template]},
        ))

        ok, message = agent_module.DIgSILENTAgent.add_transformer(
            "MCP Test Transformer",
            "Bus 02",
            "Bus 30",
            "Trf 02 - 30.ElmTr2",
            out_of_service=True,
            open_digsilent=False,
        )

        self.assertTrue(ok, message)
        self.assertEqual(len(grid.transformers), 2)
        self.assertEqual(len(high_voltage_bus.cubicles), 1)
        self.assertEqual(len(low_voltage_bus.cubicles), 1)

        created = grid.transformers[1]
        self.assertIs(
            created.GetAttribute("typ_id"),
            transformer_type,
        )
        self.assertIs(
            created.GetAttribute("bushv"),
            high_voltage_bus.cubicles[0],
        )
        self.assertIs(
            created.GetAttribute("buslv"),
            low_voltage_bus.cubicles[0],
        )
        self.assertEqual(created.GetAttribute("outserv"), 1)

        ok, message = agent_module.DIgSILENTAgent.add_transformer(
            "MCP Test Transformer",
            "Bus 02",
            "Bus 30",
            "Trf 02 - 30.ElmTr2",
            open_digsilent=False,
        )
        self.assertFalse(ok)
        self.assertIn("already exists", message)
        self.assertEqual(len(grid.transformers), 2)

        ok, message = agent_module.DIgSILENTAgent.add_transformer(
            "Same Bus Transformer",
            "Bus 02",
            "Bus 02",
            "Trf 02 - 30.ElmTr2",
            open_digsilent=False,
        )
        self.assertFalse(ok)
        self.assertIn("must be different", message)

        ok, message = agent_module.DIgSILENTAgent.add_transformer(
            "Missing Template Transformer",
            "Bus 02",
            "Bus 30",
            "Unknown.ElmTr2",
            open_digsilent=False,
        )
        self.assertFalse(ok)
        self.assertIn("Template transformer not found", message)

        failing_grid = FakeGrid("Grid")
        failing_high_voltage_bus = failing_grid.CreateObject(
            "ElmTerm",
            "Bus 02",
        )
        failing_low_voltage_bus = failing_grid.CreateObject(
            "ElmTerm",
            "Bus 30",
        )
        failing_template = failing_grid.CreateObject(
            "ElmTr2",
            "Trf 02 - 30",
        )
        failing_template.SetAttribute(
            "typ_id",
            transformer_type,
        )
        failing_grid.reject_transformer_type = True

        self.use_application(FakeApplication(
            [failing_grid],
            {"Trf 02 - 30.ElmTr2": [failing_template]},
        ))

        ok, message = agent_module.DIgSILENTAgent.add_transformer(
            "Rollback Transformer",
            "Bus 02",
            "Bus 30",
            "Trf 02 - 30.ElmTr2",
            open_digsilent=False,
        )

        self.assertFalse(ok)
        self.assertIn("rolled_back=True", message)
        self.assertEqual(
            failing_grid.transformers,
            [failing_template],
        )
        self.assertEqual(
            failing_high_voltage_bus.cubicles,
            [],
        )
        self.assertEqual(
            failing_low_voltage_bus.cubicles,
            [],
        )

if __name__ == "__main__":
    unittest.main()
