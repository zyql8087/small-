import odbAccess
from abaqusConstants import *
import odbAccess

TREATED = (19.9, 10.3, -19.5)
RAD = 0.5
COMMON = 0.0637

def analyze(path, tag):
    odb = odbAccess.openOdb(path, readOnly=True)
    inst = odb.rootAssembly.instances.values()[0]
    ep = inst.elementPoints if hasattr(inst, 'elementPoints') else None
    # gather elements within RAD of treated centroid via their centroid from connectivity
    conn = inst.elements
    import numpy as np
    nd = {k: np.array(inst.nodes[k].coordinates) for k in range(len(inst.nodes))} if False else None
    # nodes by label -> coords
    ncoords = {}
    for n in inst.nodes:
        ncoords[n.label] = n.coordinates
    sel_labels = []
    for e in conn:
        c = e.connectivity
        cs = np.array([ncoords[i] for i in c])
        if np.linalg.norm(cs.mean(0) - np.array(TREATED)) < RAD:
            sel_labels.append(e.label)
    sel = set(sel_labels)
    step = odb.steps['Step-1']
    # find frame nearest COMMON
    fr = min(step.frames, key=lambda f: abs(f.frameValue - COMMON))
    le = fr.fieldOutputs['LE'].getSubset(region=odb.rootAssembly.instances[inst.name]).values
    peak = 0.0
    for v in le:
        if v.elementLabel in sel:
            m = max(abs(x) for x in v.data)
            if m > peak: peak = m
    print("%s: frame=%.5f sel_elems=%d LE_peak=%.5f" % (tag, fr.frameValue, len(sel), peak))
    odb.close()
    return peak

analyze(r"F:/small++/paper_A_reliable_inverse_design/audits/m05_post_round6_20260921/m1m3_marlow_c3d4_20260923/m3/m3_marlow.odb", "baseline(m3_marlow)")
analyze(r"F:/small++/paper_A_reliable_inverse_design/audits/m05_post_round6_20260921/m3_hotzone_mesh_20260923/m3_hotzone_fix.odb", "treated(m3_hotzone_fix)")
