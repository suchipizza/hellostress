PLATE_TEMPLATE = """from mpi4py import MPI
from petsc4py import PETSc
from dolfinx import fem, io, mesh
from dolfinx.fem.petsc import LinearProblem
import numpy as np
import ufl
from pathlib import Path
import json

L = {{ length }}
W = {{ width }}
msh = mesh.create_rectangle(
    MPI.COMM_WORLD,
    [np.array([0.0, 0.0]), np.array([L, W])],
    [{{ mesh_nx }}, {{ mesh_ny }}],
)
V = fem.functionspace(msh, ("Lagrange", 2, (msh.geometry.dim,)))

E = {{ youngs_modulus }}
nu = {{ poisson_ratio }}
mu = E / (2.0 * (1.0 + nu))
lmbda = E * nu / ((1.0 + nu) * (1.0 - 2.0 * nu))

u = ufl.TrialFunction(V)
v = ufl.TestFunction(V)

def epsilon(field):
    return ufl.sym(ufl.grad(field))


def sigma(field):
    return 2.0 * mu * epsilon(field) + lmbda * ufl.tr(epsilon(field)) * ufl.Identity(len(field))


body_force = fem.Constant(msh, PETSc.ScalarType(({{ body_force_x }}, {{ body_force_y }})))
a = ufl.inner(sigma(u), epsilon(v)) * ufl.dx
L_form = ufl.inner(body_force, v) * ufl.dx

facets = mesh.locate_entities_boundary(msh, 1, lambda x: np.isclose(x[0], 0.0))
dofs = fem.locate_dofs_topological(V, 1, facets)
bc = fem.dirichletbc(np.array((0.0, 0.0), dtype=np.float64), dofs, V)

problem = LinearProblem(a, L_form, bcs=[bc])
w = problem.solve()
w.x.scatter_forward()

Wsig = fem.functionspace(msh, ("Discontinuous Lagrange", 0))
sigma_dev = sigma(w) - (1.0 / 3.0) * ufl.tr(sigma(w)) * ufl.Identity(len(w))
sigma_vm = ufl.sqrt((3.0 / 2.0) * ufl.inner(sigma_dev, sigma_dev))
vm_expr = fem.Expression(sigma_vm, Wsig.element.interpolation_points())
vm_h = fem.Function(Wsig)
vm_h.interpolate(vm_expr)

V_out = fem.functionspace(msh, ("Lagrange", 1, (msh.geometry.dim,)))
w_out = fem.Function(V_out)
w_out.interpolate(w)

W_out = fem.functionspace(msh, ("Lagrange", 1))
vm_out_expr = fem.Expression(sigma_vm, W_out.element.interpolation_points())
vm_out = fem.Function(W_out)
vm_out.interpolate(vm_out_expr)

disp_values = w.x.array.real.reshape((-1, msh.geometry.dim)) if w.x.array.size else np.zeros((0, msh.geometry.dim))
local_max_deflection = np.max(np.linalg.norm(disp_values, axis=1)) if disp_values.size else 0.0
local_max_stress = np.max(vm_h.x.array.real) if vm_h.x.array.size else 0.0
max_deflection = msh.comm.allreduce(local_max_deflection, op=MPI.MAX)
max_stress = msh.comm.allreduce(local_max_stress, op=MPI.MAX)

results_dir = Path("/workspace/results")
results_dir.mkdir(exist_ok=True)

with io.XDMFFile(msh.comm, str(results_dir / "displacement.xdmf"), "w") as xdmf:
    xdmf.write_mesh(msh)
    xdmf.write_function(w_out)
with io.XDMFFile(msh.comm, str(results_dir / "stress.xdmf"), "w") as xdmf:
    xdmf.write_mesh(msh)
    xdmf.write_function(vm_out)

if msh.comm.rank == 0:
    with open(results_dir / "metrics.json", "w", encoding="utf-8") as fh:
        json.dump(
            {
                "max_deflection": float(max_deflection),
                "max_stress": float(max_stress),
            },
            fh,
        )
"""
