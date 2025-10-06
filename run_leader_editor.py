import scriptcontext as sc
import Rhino
from leader_editor_panel import show_leader_editor


def run():
    try:
        if Rhino.RhinoDoc.ActiveDoc is not None:
            sc.doc = Rhino.RhinoDoc.ActiveDoc
    except Exception:
        pass
    show_leader_editor()


if __name__ == "__main__":
    run()



