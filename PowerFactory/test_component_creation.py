import unittest

import Agent_DIgSILENT as agent_module


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


class FakeGrid:
    def __init__(
        self,
        name,
        reject_voltage=False,
        reject_load_power=False,
    ):
        self.name = name
        self.reject_voltage = reject_voltage
        self.reject_load_power = reject_load_power
        self.terminals = []
        self.loads = []

    def GetAttribute(self, name):
        if name == "loc_name":
            return self.name
        raise KeyError(name)

    def GetContents(self, query, recursive):
        if query == "*.ElmTerm":
            return list(self.terminals)
        if query == "*.ElmLod":
            return list(self.loads)
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
        return None


class FakeApplication:
    def __init__(self, grids):
        self.grids = grids
        self.shown = None

    def GetCalcRelevantObjects(self, query):
        return self.grids if query == "*.ElmNet" else []

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


if __name__ == "__main__":
    unittest.main()
