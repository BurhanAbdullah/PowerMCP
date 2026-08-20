import unittest
from unittest.mock import patch

import Agent_DIgSILENT as agent_module


DEFAULTS = {
    "ElmTerm": {"uknom": 0.0, "outserv": 0},
    "ElmLod": {"bus1": None, "plini": 0.0, "qlini": 0.0, "outserv": 0},
    "ElmSym": {
        "typ_id": None,
        "bus1": None,
        "pgini": 0.0,
        "qgini": 0.0,
        "outserv": 0,
    },
    "ElmLne": {
        "typ_id": None,
        "bus1": None,
        "bus2": None,
        "dline": 0.0,
        "outserv": 0,
    },
    "ElmTr2": {
        "typ_id": None,
        "bushv": None,
        "buslv": None,
        "outserv": 0,
    },
}


class FakeObject:
    def __init__(self, parent, class_name, name):
        self.parent = parent
        self.class_name = class_name
        self.attributes = {"loc_name": name, **DEFAULTS.get(class_name, {})}
        self.objects = {}
        self.reject_attribute = None

    def __getitem__(self, class_name):
        return self.objects.setdefault(class_name, [])

    def GetAttribute(self, name):
        return self.attributes[name]

    def SetAttribute(self, name, value):
        root = self
        while root.parent is not None:
            root = root.parent
        if name != root.reject_attribute:
            self.attributes[name] = value

    def GetClassName(self):
        return self.class_name

    def GetFullName(self):
        prefix = self.parent.GetFullName() if self.parent else r"\user"
        return f"{prefix}\\{self.attributes['loc_name']}.{self.class_name}"

    def GetParent(self):
        return self.parent

    def GetContents(self, query, recursive):
        return list(self[query.rsplit(".", 1)[-1]])

    def CreateObject(self, class_name, name):
        obj = FakeObject(self, class_name, name)
        self[class_name].append(obj)
        return obj

    def Delete(self):
        self.parent[self.class_name].remove(self)


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

    def network(self, bus_names=(), template=None):
        grid = FakeObject(None, "ElmNet", "Grid")
        buses = {
            name: grid.CreateObject("ElmTerm", name)
            for name in bus_names
        }
        objects = {}
        template_object = template_type = None
        if template:
            query, class_name, type_class = template
            template_type = FakeObject(None, type_class, "Test Type")
            template_object = grid.CreateObject(
                class_name,
                query.rsplit(".", 1)[0],
            )
            template_object.SetAttribute("typ_id", template_type)
            objects[query] = [template_object]
        self.use_application(FakeApplication([grid], objects))
        return grid, buses, template_object, template_type

    def assert_failed(self, result, text):
        ok, message = result
        self.assertFalse(ok)
        self.assertIn(text, message)
        return message

    def assert_attributes(self, obj, expected):
        for name, value in expected.items():
            self.assertEqual(obj.GetAttribute(name), value)

    def test_add_bus_validation_and_rollback(self):
        grid, _, _, _ = self.network()
        ok, message = agent_module.DIgSILENTAgent.add_bus(
            "MCP Test Bus", 110.0, open_digsilent=False
        )
        self.assertTrue(ok, message)
        self.assert_attributes(
            grid["ElmTerm"][0],
            {"uknom": 110.0, "outserv": 0},
        )

        self.assert_failed(
            agent_module.DIgSILENTAgent.add_bus(
                "MCP Test Bus", 110.0, open_digsilent=False
            ),
            "already exists",
        )
        self.assert_failed(
            agent_module.DIgSILENTAgent.add_bus(
                "Invalid Bus", -1.0, open_digsilent=False
            ),
            "finite positive",
        )
        self.assertEqual(len(grid["ElmTerm"]), 1)

        grid_a = FakeObject(None, "ElmNet", "Grid A")
        grid_b = FakeObject(None, "ElmNet", "Grid B")
        self.use_application(FakeApplication([grid_a, grid_b]))
        self.assert_failed(
            agent_module.DIgSILENTAgent.add_bus(
                "Ambiguous Bus", 20.0, open_digsilent=False
            ),
            "Multiple grids",
        )
        ok, message = agent_module.DIgSILENTAgent.add_bus(
            "Selected Bus",
            20.0,
            grid_name="Grid B",
            out_of_service=True,
            open_digsilent=False,
        )
        self.assertTrue(ok, message)
        self.assertEqual(grid_a["ElmTerm"], [])
        self.assertEqual(grid_b["ElmTerm"][0].GetAttribute("outserv"), 1)

        failing_grid, _, _, _ = self.network()
        failing_grid.reject_attribute = "uknom"
        self.assert_failed(
            agent_module.DIgSILENTAgent.add_bus(
                "Rollback Bus", 110.0, open_digsilent=False
            ),
            "rolled_back=True",
        )
        self.assertEqual(failing_grid["ElmTerm"], [])

    def test_add_load_validation_and_rollback(self):
        grid, buses, _, _ = self.network(("Bus 01",))
        bus = buses["Bus 01"]
        ok, message = agent_module.DIgSILENTAgent.add_load(
            "MCP Test Load",
            "Bus 01",
            50.0,
            12.5,
            out_of_service=True,
            open_digsilent=False,
        )
        self.assertTrue(ok, message)
        created = grid["ElmLod"][0]
        self.assertIs(created.GetAttribute("bus1"), bus["StaCubic"][0])
        self.assert_attributes(
            created,
            {"plini": 50.0, "qlini": 12.5, "outserv": 1},
        )

        self.assert_failed(
            agent_module.DIgSILENTAgent.add_load(
                "MCP Test Load", "Bus 01", 50.0, open_digsilent=False
            ),
            "already exists",
        )
        self.assert_failed(
            agent_module.DIgSILENTAgent.add_load(
                "Missing Bus Load", "Unknown Bus", 10.0, open_digsilent=False
            ),
            "Bus not found",
        )
        self.assert_failed(
            agent_module.DIgSILENTAgent.add_load(
                "Invalid Load", "Bus 01", -1.0, open_digsilent=False
            ),
            "finite and non-negative",
        )

        failing_grid, buses, _, _ = self.network(("Bus 01",))
        failing_grid.reject_attribute = "plini"
        self.assert_failed(
            agent_module.DIgSILENTAgent.add_load(
                "Rollback Load", "Bus 01", 10.0, open_digsilent=False
            ),
            "rolled_back=True",
        )
        self.assertEqual(failing_grid["ElmLod"], [])
        self.assertEqual(buses["Bus 01"]["StaCubic"], [])

    def test_add_generator_validation_and_rollback(self):
        template = ("G 01.ElmSym", "ElmSym", "TypSym")
        grid, buses, template_object, machine_type = self.network(
            ("Bus 01",), template
        )
        ok, message = agent_module.DIgSILENTAgent.add_generator(
            "MCP Test Generator",
            "Bus 01",
            template[0],
            25.0,
            5.0,
            out_of_service=True,
            open_digsilent=False,
        )
        self.assertTrue(ok, message)
        created = grid["ElmSym"][1]
        self.assertIs(created.GetAttribute("typ_id"), machine_type)
        self.assertIs(
            created.GetAttribute("bus1"), buses["Bus 01"]["StaCubic"][0]
        )
        self.assert_attributes(
            created,
            {"pgini": 25.0, "qgini": 5.0, "outserv": 1},
        )

        self.assert_failed(
            agent_module.DIgSILENTAgent.add_generator(
                "MCP Test Generator",
                "Bus 01",
                template[0],
                25.0,
                open_digsilent=False,
            ),
            "already exists",
        )
        self.assert_failed(
            agent_module.DIgSILENTAgent.add_generator(
                "Missing Template Generator",
                "Bus 01",
                "Unknown.ElmSym",
                10.0,
                open_digsilent=False,
            ),
            "Template generator not found",
        )

        failing_grid, buses, failing_template, _ = self.network(
            ("Bus 01",), template
        )
        failing_grid.reject_attribute = "pgini"
        self.assert_failed(
            agent_module.DIgSILENTAgent.add_generator(
                "Rollback Generator",
                "Bus 01",
                template[0],
                10.0,
                open_digsilent=False,
            ),
            "rolled_back=True",
        )
        self.assertEqual(failing_grid["ElmSym"], [failing_template])
        self.assertEqual(buses["Bus 01"]["StaCubic"], [])
        self.assertIsNotNone(template_object)

    def test_add_line_validation_and_rollback(self):
        template = ("Line 01 - 02.ElmLne", "ElmLne", "TypLne")
        grid, buses, _, line_type = self.network(
            ("Bus 01", "Bus 02"), template
        )
        ok, message = agent_module.DIgSILENTAgent.add_line(
            "MCP Test Line",
            "Bus 01",
            "Bus 02",
            template[0],
            10.0,
            out_of_service=True,
            open_digsilent=False,
        )
        self.assertTrue(ok, message)
        created = grid["ElmLne"][1]
        self.assertIs(created.GetAttribute("typ_id"), line_type)
        self.assertIs(
            created.GetAttribute("bus1"), buses["Bus 01"]["StaCubic"][0]
        )
        self.assertIs(
            created.GetAttribute("bus2"), buses["Bus 02"]["StaCubic"][0]
        )
        self.assert_attributes(created, {"dline": 10.0, "outserv": 1})

        duplicate = agent_module.DIgSILENTAgent.add_line(
            "MCP Test Line",
            "Bus 01",
            "Bus 02",
            template[0],
            10.0,
            open_digsilent=False,
        )
        self.assert_failed(duplicate, "already exists")
        self.assert_failed(
            agent_module.DIgSILENTAgent.add_line(
                "Same Bus Line",
                "Bus 01",
                "Bus 01",
                template[0],
                10.0,
                open_digsilent=False,
            ),
            "must be different",
        )
        self.assert_failed(
            agent_module.DIgSILENTAgent.add_line(
                "Missing Template Line",
                "Bus 01",
                "Bus 02",
                "Unknown.ElmLne",
                10.0,
                open_digsilent=False,
            ),
            "Template line not found",
        )

        failing_grid, buses, failing_template, _ = self.network(
            ("Bus 01", "Bus 02"), template
        )
        failing_grid.reject_attribute = "dline"
        self.assert_failed(
            agent_module.DIgSILENTAgent.add_line(
                "Rollback Line",
                "Bus 01",
                "Bus 02",
                template[0],
                10.0,
                open_digsilent=False,
            ),
            "rolled_back=True",
        )
        self.assertEqual(failing_grid["ElmLne"], [failing_template])
        self.assertEqual(buses["Bus 01"]["StaCubic"], [])
        self.assertEqual(buses["Bus 02"]["StaCubic"], [])

    def test_add_transformer_validation_and_rollback(self):
        template = ("Trf 02 - 30.ElmTr2", "ElmTr2", "TypTr2")
        grid, buses, _, transformer_type = self.network(
            ("Bus 02", "Bus 30"), template
        )
        ok, message = agent_module.DIgSILENTAgent.add_transformer(
            "MCP Test Transformer",
            "Bus 02",
            "Bus 30",
            template[0],
            out_of_service=True,
            open_digsilent=False,
        )
        self.assertTrue(ok, message)
        created = grid["ElmTr2"][1]
        self.assertIs(created.GetAttribute("typ_id"), transformer_type)
        self.assertIs(
            created.GetAttribute("bushv"), buses["Bus 02"]["StaCubic"][0]
        )
        self.assertIs(
            created.GetAttribute("buslv"), buses["Bus 30"]["StaCubic"][0]
        )
        self.assertEqual(created.GetAttribute("outserv"), 1)

        self.assert_failed(
            agent_module.DIgSILENTAgent.add_transformer(
                "MCP Test Transformer",
                "Bus 02",
                "Bus 30",
                template[0],
                open_digsilent=False,
            ),
            "already exists",
        )
        self.assert_failed(
            agent_module.DIgSILENTAgent.add_transformer(
                "Same Bus Transformer",
                "Bus 02",
                "Bus 02",
                template[0],
                open_digsilent=False,
            ),
            "must be different",
        )
        self.assert_failed(
            agent_module.DIgSILENTAgent.add_transformer(
                "Missing Template Transformer",
                "Bus 02",
                "Bus 30",
                "Unknown.ElmTr2",
                open_digsilent=False,
            ),
            "Template transformer not found",
        )

        failing_grid, buses, failing_template, _ = self.network(
            ("Bus 02", "Bus 30"), template
        )
        failing_grid.reject_attribute = "typ_id"
        self.assert_failed(
            agent_module.DIgSILENTAgent.add_transformer(
                "Rollback Transformer",
                "Bus 02",
                "Bus 30",
                template[0],
                open_digsilent=False,
            ),
            "rolled_back=True",
        )
        self.assertEqual(failing_grid["ElmTr2"], [failing_template])
        self.assertEqual(buses["Bus 02"]["StaCubic"], [])
        self.assertEqual(buses["Bus 30"]["StaCubic"], [])

    def test_add_component_dispatch_and_validation(self):
        cases = [
            (
                "bus",
                "add_bus",
                {"nominal_voltage_kv": 110.0},
                ("New Component", 110.0, "Grid", True, False),
            ),
            (
                "load",
                "add_load",
                {
                    "bus_name": "Bus 01",
                    "active_power_mw": 1.0,
                    "reactive_power_mvar": 0.25,
                },
                (
                    "New Component",
                    "Bus 01",
                    1.0,
                    0.25,
                    "Grid",
                    True,
                    False,
                ),
            ),
            (
                "generator",
                "add_generator",
                {
                    "bus_name": "Bus 01",
                    "template_generator": "G 01.ElmSym",
                    "active_power_mw": 1.0,
                },
                (
                    "New Component",
                    "Bus 01",
                    "G 01.ElmSym",
                    1.0,
                    0.0,
                    "Grid",
                    True,
                    False,
                ),
            ),
            (
                "line",
                "add_line",
                {
                    "bus1_name": "Bus 01",
                    "bus2_name": "Bus 02",
                    "template_line": "Line 01 - 02.ElmLne",
                    "length_km": 1.0,
                },
                (
                    "New Component",
                    "Bus 01",
                    "Bus 02",
                    "Line 01 - 02.ElmLne",
                    1.0,
                    "Grid",
                    True,
                    False,
                ),
            ),
            (
                "transformer",
                "add_transformer",
                {
                    "high_voltage_bus_name": "Bus 02",
                    "low_voltage_bus_name": "Bus 30",
                    "template_transformer": "Trf 02 - 30.ElmTr2",
                },
                (
                    "New Component",
                    "Bus 02",
                    "Bus 30",
                    "Trf 02 - 30.ElmTr2",
                    "Grid",
                    True,
                    False,
                ),
            ),
        ]

        for kind, method_name, parameters, expected_args in cases:
            with self.subTest(component_type=kind):
                with patch.object(
                    agent_module.DIgSILENTAgent,
                    method_name,
                    return_value=(True, kind),
                ) as method:
                    result = agent_module.DIgSILENTAgent.add_component(
                        kind,
                        "New Component",
                        parameters,
                        "Grid",
                        True,
                        False,
                    )

                    self.assertEqual((True, kind), result)
                    method.assert_called_once_with(*expected_args)

        self.assert_failed(
            agent_module.DIgSILENTAgent.add_component(
                "unknown",
                "New Component",
                {},
            ),
            "Unsupported component type",
        )

        self.assert_failed(
            agent_module.DIgSILENTAgent.add_component(
                "load",
                "New Component",
                {"bus_name": "Bus 01"},
            ),
            "Missing parameter(s)",
        )

        self.assert_failed(
            agent_module.DIgSILENTAgent.add_component(
                "bus",
                "New Component",
                {
                    "nominal_voltage_kv": 110.0,
                    "bus_name": "Unexpected",
                },
            ),
            "Unsupported parameter(s)",
        )

    def test_delete_component_requires_confirmation_and_cleans_connections(self):
        template = ("Line 01 - 02.ElmLne", "ElmLne", "TypLne")
        grid, buses, template_line, _ = self.network(
            ("Bus 01", "Bus 02"), template
        )

        ok, message = agent_module.DIgSILENTAgent.add_line(
            "MCP Test Line",
            "Bus 01",
            "Bus 02",
            template[0],
            1.0,
            open_digsilent=False,
        )
        self.assertTrue(ok, message)

        ok, message = agent_module.DIgSILENTAgent.delete_component(
            "line",
            "MCP Test Line",
            open_digsilent=False,
        )
        self.assertTrue(ok, message)
        self.assertIn(
            "confirmation_required=DELETE line MCP Test Line",
            message,
        )
        self.assertEqual(len(grid["ElmLne"]), 2)

        self.assert_failed(
            agent_module.DIgSILENTAgent.delete_component(
                "line",
                "MCP Test Line",
                confirmation="DELETE line wrong name",
                open_digsilent=False,
            ),
            "confirmation must exactly match",
        )

        self.assert_failed(
            agent_module.DIgSILENTAgent.delete_component(
                "bus",
                "Bus 01",
                confirmation="DELETE bus Bus 01",
                open_digsilent=False,
            ),
            "connected cubicles",
        )

        ok, message = agent_module.DIgSILENTAgent.delete_component(
            "line",
            "MCP Test Line",
            confirmation="DELETE line MCP Test Line",
            open_digsilent=False,
        )
        self.assertTrue(ok, message)
        self.assertEqual(grid["ElmLne"], [template_line])
        self.assertEqual(buses["Bus 01"]["StaCubic"], [])
        self.assertEqual(buses["Bus 02"]["StaCubic"], [])

        ok, message = agent_module.DIgSILENTAgent.delete_component(
            "bus",
            "Bus 01",
            confirmation="DELETE bus Bus 01",
            open_digsilent=False,
        )
        self.assertTrue(ok, message)
        self.assertNotIn(buses["Bus 01"], grid["ElmTerm"])


if __name__ == "__main__":
    unittest.main()
