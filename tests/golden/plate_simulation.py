from dolfin import *
import numpy as np
from pathlib import Path
import json

L = 0.5
W = 0.3
mesh = RectangleMesh(Point(0.0, 0.0), Point(L, W), 32, 16)
V = VectorFunctionSpace(mesh, "P", 2)

E = 70000000000.0
nu = 0.33
mu = E / (2.0 * (1.0 + nu))
lmbda = E * nu / ((1 + nu) * (1 - 2 * nu))

class Left(SubDomain):
    def inside(self, x, on_boundary):
        return on_boundary and near(x[0], 0.0)

left = Left()
bcs = [DirichletBC(V, Constant((0.0, 0.0)), left)]

u = TrialFunction(V)
v = TestFunction(V)
d = u.geometric_dimension()
I = Identity(d)


def epsilon(u):
    return sym(grad(u))


def sigma(u):
    return lmbda * div(u) * I + 2 * mu * epsilon(u)

body_force = Constant((0.0, 50000.0))
a = inner(sigma(u), epsilon(v)) * dx
L_form = dot(body_force, v) * dx

w = Function(V)
problem = LinearVariationalProblem(a, L_form, w, bcs)
solver = LinearVariationalSolver(problem)
solver.solve()
V_sig = FunctionSpace(mesh, "P", 1)
vm_expr = project(sqrt(3.0 / 2.0 * inner(dev(sigma(w)), dev(sigma(w)))), V_sig)

max_deflection = np.max(np.abs(w.compute_vertex_values(mesh)))
max_stress = np.max(vm_expr.compute_vertex_values(mesh))

results_dir = Path("results")
results_dir.mkdir(exist_ok=True)

with XDMFFile(str(results_dir / "displacement.xdmf")) as xdmf:
    xdmf.write(w)
with XDMFFile(str(results_dir / "stress.xdmf")) as xdmf:
    xdmf.write(vm_expr)

with open(results_dir / "metrics.json", "w", encoding="utf-8") as fh:
    json.dump({
        "max_deflection": float(max_deflection),
        "max_stress": float(max_stress)
    }, fh)
