function GenerateSnapProbeCurves(parameterCsv, outputDir, varargin)
% SNAP-THROUGH PROBE generator (large-deformation, displacement / arc-length control).
%
% Goal of this probe: find out whether driving the Miura sheet into LARGE
% deformation with DISPLACEMENT / ARC-LENGTH control produces qualitatively
% diverse force-displacement curves (plateaus, negative-stiffness, snap-back,
% multi-peak) instead of the monotone mild-hardening curves we get from the
% small-deformation force-controlled (NR) generator.
%
% It reuses the SAME geometry + material setup as the production generator
% (GenerateOrigamiForceDisplacementCurves.m): L=0.2, gamma=70deg, panelE/creaseE
% from the parameter row, Poisson=0.3, rho=1200. ONLY the loading is changed.
%
% Loading modes (LoadingMode):
%   "displacement_dc"  -> ControllerDCLoading   (generalized displacement / arc-length;
%                         captures snap-THROUGH, monotone-ish displacement axis). DEFAULT.
%   "arclength_mgdcm"  -> ControllerMGDCMLoading (modified GDCM; most robust, captures
%                         snap-BACK too; displacement axis may be non-monotone).
%   "force_nr"         -> ControllerNRLoading    (force ramp; reference / baseline only).
%
% Force is recovered as: force(i) = loadHis(i) * (nForceNodes * RefUnitForce),
% because the DC/MGDCM solvers store loadHis = load factor lambda and the applied
% load = lambda * referenceLoadVector (see Solver_LoadingDC.m).
%
% Dependencies on MATLAB path: OrigamiSolver, GenerateMiuraSheet, GenerateTMPSheet,
%   ControllerDCLoading, ControllerMGDCMLoading, ControllerNRLoading.
%
% NOTE for codex: lambdaBar / RefUnitForce / iterMax almost certainly need TUNING
% per-pattern so that 80 arc-length steps span a meaningfully large deformation.
% Start from the defaults below; if curves stop too early (small deformation) raise
% lambdaBar; if the solver diverges, lower lambdaBar and raise iterMax.

p = inputParser;
addRequired(p, 'parameterCsv');
addRequired(p, 'outputDir');
addParameter(p, 'SimulatorRoot', "");
addParameter(p, 'CurvePoints', 80);
addParameter(p, 'LoadingMode', "displacement_dc");
addParameter(p, 'LambdaBar', 0.5);          % arc-length step size (TUNE)
addParameter(p, 'RefUnitForce', 1.0);       % reference unit force per loaded node (N)
addParameter(p, 'IterMax', 50);
addParameter(p, 'Tol', 1e-7);
addParameter(p, 'StartIndex', 1);
addParameter(p, 'EndIndex', inf);
addParameter(p, 'Overwrite', false);
addParameter(p, 'RequireMiuraOnly', true);
parse(p, parameterCsv, outputDir, varargin{:});

parameterCsv = string(p.Results.parameterCsv);
outputDir    = string(p.Results.outputDir);
simulatorRoot= string(p.Results.SimulatorRoot);
curvePoints  = double(p.Results.CurvePoints);
loadingMode  = string(p.Results.LoadingMode);
lambdaBar    = double(p.Results.LambdaBar);
refUnitForce = double(p.Results.RefUnitForce);
iterMax      = double(p.Results.IterMax);
tol          = double(p.Results.Tol);
startIndex   = double(p.Results.StartIndex);
endIndex     = double(p.Results.EndIndex);
overwrite    = logical(p.Results.Overwrite);
requireMiuraOnly = logical(p.Results.RequireMiuraOnly);

if ~isfolder(outputDir); mkdir(outputDir); end
if strlength(simulatorRoot) > 0; addpath(genpath(simulatorRoot)); end

conditions = makeConditionTable();
params = readtable(parameterCsv);
if isinf(endIndex); endIndex = height(params); else; endIndex = min(endIndex, height(params)); end
startIndex = max(1, startIndex);

fprintf('SNAP PROBE | mode=%s | rows %d:%d | curvePoints=%d | lambdaBar=%g\n', ...
    loadingMode, startIndex, endIndex, curvePoints, lambdaBar);

for rowIndex = startIndex:endIndex
    row = params(rowIndex, :);
    sampleId = string(row.sample_id);
    outCsv = fullfile(outputDir, char(sampleId + ".csv"));
    if isfile(outCsv) && ~overwrite
        fprintf('[SKIP] %s\n', sampleId); continue;
    end
    try
        sampleCurves = table();
        for c = 1:height(conditions)
            cond = conditions(c, :);
            ori = buildOrigami(row, double(cond.deployment));
            curveTable = runLoadCaseDispControl(ori, sampleId, double(cond.curve_id), ...
                string(cond.load_case), double(cond.deployment), string(cond.response_axis), ...
                curvePoints, loadingMode, lambdaBar, refUnitForce, iterMax, tol);
            sampleCurves = [sampleCurves; curveTable]; %#ok<AGROW>
        end
        writetable(sampleCurves, outCsv);
        fprintf('[OK] %s -> %s\n', sampleId, outCsv);
    catch ME
        logFailure(outputDir, sampleId, rowIndex, ME);
        fprintf('[FAIL] %s: %s\n', sampleId, ME.message);
    end
end
end


function conditions = makeConditionTable()
curve_id      = (0:5)';
load_case     = ["bending";"bending";"bending";"axial";"axial";"axial"];
deployment    = [0.3;0.6;0.9;0.3;0.6;0.9];
response_axis = ["z";"z";"z";"x";"x";"x"];
conditions = table(curve_id, load_case, deployment, response_axis);
end


function ori = buildOrigami(row, deployment)
% Identical geometry/material setup to the production generator.
rho = 1200; L = 0.2;
pattern = double(row.pattern); m = double(row.m); n = double(row.n);
tcrease = double(row.tcrease); tpanel = double(row.tpanel); W = double(row.W);
creaseE = double(row.creaseE); panelE = double(row.panelE);

ori = OrigamiSolver; ori.showNumber = 0;
if pattern == 1
    gama = 70*pi/180; b = L/m; a = (L - b*cot(gama))/n;
    [ori.node0, ori.panel0] = GenerateMiuraSheet(a, b, gama, m, n, deployment);
elseif pattern == 2
    b = L/m; a = L/n;
    [ori.node0, ori.panel0] = GenerateTMPSheet(a, b, m, n, deployment);
else
    error('Unsupported pattern: %g', pattern);
end
ori.Mesh_AnalyzeOriginalPattern();
ori.displayRange = L; ori.displayRangeRatio = 0.1;

creaseIndex = ori.oldCreaseType ~= 1;
ori.creaseWidthVec = zeros(ori.oldCreaseNum, 1);
ori.creaseWidthVec(creaseIndex) = W;
ori.compliantCreaseOpen = 0; ori.mesh2D3D = 3;
ori.Mesh_Mesh();

ori.panelE = panelE; ori.creaseE = creaseE;
ori.panelPoisson = 0.3; ori.creasePoisson = 0.3;
ori.panelThickVec = tpanel*ones(size(ori.panel0,2),1); ori.panelW = W;
ori.creaseThickVec = zeros(ori.oldCreaseNum,1); ori.creaseThickVec(creaseIndex) = tcrease;
ori.densityCrease = rho; ori.densityPanel = rho;
end


function curveTable = runLoadCaseDispControl(ori, sampleId, curveId, loadCase, deployment, ...
        responseAxis, curvePoints, loadingMode, lambdaBar, refUnitForce, iterMax, tol)
% Same support/loading node identification as the production NR generator, but
% drive with displacement/arc-length control to capture snap-through.

xCoord = ori.newNode(:,1);
tolNode = max(1e-10, 1e-8*max(abs(xCoord)));
supNode   = find(abs(xCoord - min(xCoord)) <= tolNode);   % min-x edge: clamped
forceNode = find(abs(xCoord - max(xCoord)) <= tolNode);   % max-x edge: loaded
if isempty(supNode) || isempty(forceNode) || ~isempty(intersect(supNode, forceNode))
    error('Bad support/force node set.');
end

if loadCase == "bending"; axisIndex = 3; sgn = -1;   % out-of-plane -z
elseif loadCase == "axial"; axisIndex = 1; sgn = +1; % in-plane +x (accordion fold/unfold)
else; error('Unsupported load case: %s', loadCase); end

% Reference unit load pattern at the loaded edge along the load axis.
loadComponents = zeros(length(forceNode), 3);
loadComponents(:, axisIndex) = sgn*refUnitForce;

switch loadingMode
    case "displacement_dc";  ctrl = ControllerDCLoading;  useDC = true;
    case "arclength_mgdcm";  ctrl = ControllerMGDCMLoading; useDC = false;
    case "force_nr";         ctrl = ControllerNRLoading;   useDC = false;
    otherwise; error('Unknown LoadingMode: %s', loadingMode);
end
ctrl.supp = [supNode, ones(length(supNode), 3)];
ctrl.load = [forceNode, loadComponents];
ctrl.increStep = curvePoints; ctrl.tol = tol; ctrl.iterMax = iterMax;
ctrl.plotOpen = 0; ctrl.videoOpen = 0; ctrl.detailFigOpen = 0;
if isprop(ctrl, 'lambdaBar'); ctrl.lambdaBar = lambdaBar; end
if useDC  % DC needs an explicit reference DOF: first loaded node along the load axis
    ctrl.selectedRefDisp = [forceNode(1), axisIndex];
end

if loadingMode == "force_nr"
    ori.loadingController{1} = {"NR", ctrl};
elseif loadingMode == "displacement_dc"
    ori.loadingController{1} = {"DC", ctrl};
else
    ori.loadingController{1} = {"MGDCM", ctrl};
end
ori.Solver_Solve();

avail = min(curvePoints, size(ctrl.Uhis, 1));
step = (1:curvePoints)';
displacement = nan(curvePoints,1); signed_displacement = nan(curvePoints,1);
u = ctrl.Uhis(1:avail, forceNode, axisIndex);
displacement(1:avail)        = reshape(mean(abs(u), 2), [], 1);
signed_displacement(1:avail) = reshape(mean(u, 2), [], 1);

% Force = load factor lambda * total reference load magnitude along the axis.
refTotal = sum(abs(loadComponents(:, axisIndex)));      % = nForceNodes * refUnitForce
force = nan(curvePoints,1); signed_force = nan(curvePoints,1);
if loadingMode == "force_nr"
    forcePerStep = refTotal; force(1:avail) = step(1:avail)*forcePerStep;     % NR: linear ramp
    signed_force(1:avail) = sgn*force(1:avail);
else
    lam = reshape(ctrl.loadHis(1:avail), [], 1);          % loadHis stores lambda
    force(1:avail)        = abs(lam)*refTotal;
    signed_force(1:avail) = sgn*lam*refTotal;
end
converged = isfinite(displacement) & isfinite(force);

% Physics histories (same channels as production schema).
energy = historyMatrix(ctrl, 'strainEnergyHis', curvePoints, 4);
strain_energy_crease = energy(:,1) + energy(:,4);
strain_energy_panel  = energy(:,2) + energy(:,3);
strain_energy_total  = strain_energy_crease + strain_energy_panel;
max_bar_stress    = maxAbsHistory(ctrl, 'barSxHis', curvePoints);
max_bar_strain    = maxAbsHistory(ctrl, 'barExHis', curvePoints);
max_crease_moment = maxAbsHistory(ctrl, 'sprMHis', curvePoints);
max_crease_rotation = maxAbsHistory(ctrl, 'sprRotHis', curvePoints);

n = curvePoints;
curveTable = table( ...
    repmat(sampleId,n,1), repmat(curveId,n,1), repmat(loadCase,n,1), ...
    repmat(deployment,n,1), repmat(responseAxis,n,1), step, ...
    force, displacement, signed_force, signed_displacement, converged, ...
    strain_energy_total, strain_energy_crease, strain_energy_panel, ...
    max_bar_stress, max_bar_strain, max_crease_moment, max_crease_rotation, ...
    repmat(string(loadingMode),n,1), repmat(lambdaBar,n,1), ...
    'VariableNames', {'sample_id','curve_id','load_case','deployment','response_axis','step', ...
    'force','displacement','signed_force','signed_displacement','converged', ...
    'strain_energy_total','strain_energy_crease','strain_energy_panel', ...
    'max_bar_stress','max_bar_strain','max_crease_moment','max_crease_rotation', ...
    'loading_mode','lambda_bar'});
end


function h = historyMatrix(ctrl, name, curvePoints, minCols)
h = nan(curvePoints, minCols);
if ~isprop(ctrl, name) || isempty(ctrl.(name)); return; end
raw = ctrl.(name); r = min(curvePoints, size(raw,1)); c = min(size(raw,2), minCols);
h(1:r, 1:c) = raw(1:r, 1:c);
end

function v = maxAbsHistory(ctrl, name, curvePoints)
v = nan(curvePoints, 1);
if ~isprop(ctrl, name) || isempty(ctrl.(name)); return; end
raw = ctrl.(name); r = min(curvePoints, size(raw,1));
v(1:r) = max(abs(raw(1:r, :)), [], 2);
end

function logFailure(outputDir, sampleId, rowIndex, ME)
fid = fopen(fullfile(outputDir, 'failures.log'), 'a'); if fid < 0; return; end
c = onCleanup(@() fclose(fid));
fprintf(fid, '[%s] row=%d id=%s :: %s\n', datestr(now,31), rowIndex, sampleId, ME.message);
end
