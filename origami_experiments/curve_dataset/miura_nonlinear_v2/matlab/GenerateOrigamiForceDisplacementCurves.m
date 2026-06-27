function GenerateOrigamiForceDisplacementCurves(parameterCsv, outputDir, varargin)
% Generate force-displacement curve CSV files for the origami canopy dataset.
%
% This keeps the original GenerateOrigamiDataSet parameter and loading logic:
%   pattern, m, n, tcrease, tpanel, W, creaseE, panelE
% and exports six discretized response curves per sample:
%   bending/axial at deployment = 0.3, 0.6, 0.9
%
% Each sample is written to:
%   <outputDir>/<sample_id>.csv
%
% Required dependencies on the MATLAB path:
%   OrigamiSimulator / SWOMPS classes:
%   OrigamiSolver, ControllerNRLoading, GenerateMiuraSheet

p = inputParser;
addRequired(p, 'parameterCsv');
addRequired(p, 'outputDir');
addParameter(p, 'SimulatorRoot', "");
addParameter(p, 'CurvePoints', 80);
addParameter(p, 'FinalLoad', 3);
addParameter(p, 'FinalLoadMode', "stiffness_scaled");
addParameter(p, 'TargetLinearDisplacement', 0.015);
addParameter(p, 'MaxFinalLoad', 10000);
addParameter(p, 'StartIndex', 1);
addParameter(p, 'EndIndex', inf);
addParameter(p, 'Overwrite', false);
addParameter(p, 'PlotOpen', false);
addParameter(p, 'RequireMiuraOnly', false);
addParameter(p, 'RequirePhysics', true);
parse(p, parameterCsv, outputDir, varargin{:});

parameterCsv = string(p.Results.parameterCsv);
outputDir = string(p.Results.outputDir);
simulatorRoot = string(p.Results.SimulatorRoot);
curvePoints = double(p.Results.CurvePoints);
finalLoad = double(p.Results.FinalLoad);
finalLoadMode = string(p.Results.FinalLoadMode);
targetLinearDisplacement = double(p.Results.TargetLinearDisplacement);
maxFinalLoad = double(p.Results.MaxFinalLoad);
startIndex = double(p.Results.StartIndex);
endIndex = double(p.Results.EndIndex);
overwrite = logical(p.Results.Overwrite);
plotOpen = logical(p.Results.PlotOpen);
requireMiuraOnly = logical(p.Results.RequireMiuraOnly);
requirePhysics = logical(p.Results.RequirePhysics);

if curvePoints < 2
    error('CurvePoints must be at least 2.');
end
if finalLoad <= 0
    error('FinalLoad must be positive.');
end
if targetLinearDisplacement <= 0
    error('TargetLinearDisplacement must be positive.');
end
if maxFinalLoad <= 0
    error('MaxFinalLoad must be positive.');
end
if finalLoadMode ~= "fixed" && finalLoadMode ~= "stiffness_scaled"
    error('FinalLoadMode must be fixed or stiffness_scaled.');
end
if ~isfolder(outputDir)
    mkdir(outputDir);
end

scriptDir = fileparts(mfilename('fullpath'));
projectRoot = fileparts(fileparts(fileparts(scriptDir)));
addGenerateOrigamiDataSetPaths(projectRoot);
if strlength(simulatorRoot) > 0
    addpath(genpath(simulatorRoot));
end
assertDependencies(requireMiuraOnly);

params = readtable(parameterCsv);
if requireMiuraOnly
    if ~ismember('pattern', params.Properties.VariableNames)
        error('Miura-only mode requires a pattern column in the parameter table.');
    end
    nonMiuraRows = find(double(params.pattern) ~= 1);
    if ~isempty(nonMiuraRows)
        preview = strjoin(string(nonMiuraRows(1:min(5, numel(nonMiuraRows)))), ', ');
        error('Miura-only mode found non-Miura pattern rows at table indices: %s', preview);
    end
end
conditions = makeConditionTable();

if isinf(endIndex)
    endIndex = height(params);
else
    endIndex = min(endIndex, height(params));
end
startIndex = max(1, startIndex);

fprintf('Generating origami curve responses for rows %d:%d\n', startIndex, endIndex);
fprintf('Curve points per condition: %d\n', curvePoints);
fprintf('Final load mode: %s\n', finalLoadMode);
if finalLoadMode == "fixed"
    fprintf('Final total load per curve: %.12g\n', finalLoad);
else
    fprintf('Target linear displacement per curve: %.12g\n', targetLinearDisplacement);
    fprintf('Max final load cap: %.12g\n', maxFinalLoad);
end

for rowIndex = startIndex:endIndex
    row = params(rowIndex, :);
    sampleId = string(row.sample_id);
    outCsv = fullfile(outputDir, char(sampleId + ".csv"));

    if isfile(outCsv) && ~overwrite
        fprintf('[SKIP] %s already exists\n', sampleId);
        continue;
    end

    try
        sampleCurves = table();
        for conditionIndex = 1:height(conditions)
            cond = conditions(conditionIndex, :);
            ori = buildOrigami(row, double(cond.deployment), plotOpen);
            curveTable = runLoadCase( ...
                ori, sampleId, double(cond.curve_id), string(cond.load_case), ...
                double(cond.deployment), string(cond.response_axis), curvePoints, ...
                row, finalLoad, finalLoadMode, targetLinearDisplacement, maxFinalLoad, ...
                plotOpen, requirePhysics);
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


function addGenerateOrigamiDataSetPaths(projectRoot)
dataSetRoot = fullfile(projectRoot, 'external', 'GenerateOrigamiDataSet');
requiredPaths = { ...
    fullfile(dataSetRoot, 'Data_Origami_Sheet_MaterialProperty'), ...
    fullfile(dataSetRoot, 'Data_Origami_Sheet_MaterialProperty', 'Miura'), ...
    fullfile(dataSetRoot, 'Data_Origami_Sheet_MaterialProperty', 'TMP')};

for i = 1:numel(requiredPaths)
    pathToAdd = requiredPaths{i};
    if isfolder(pathToAdd)
        addpath(pathToAdd);
    end
end
end


function assertDependencies(requireMiuraOnly)
requiredNames = ["OrigamiSolver", "ControllerNRLoading", "GenerateMiuraSheet"];
if ~requireMiuraOnly
    requiredNames(end + 1) = "GenerateTMPSheet";
end
missing = strings(0, 1);
for i = 1:numel(requiredNames)
    name = requiredNames(i);
    if exist(name, 'file') == 0 && exist(name, 'class') == 0
        missing(end + 1, 1) = name; %#ok<AGROW>
    end
end
if ~isempty(missing)
    error('Missing MATLAB/SWOMPS dependencies on path: %s', strjoin(missing, ', '));
end
end


function conditions = makeConditionTable()
curve_id = (0:5)';
load_case = ["bending"; "bending"; "bending"; "axial"; "axial"; "axial"];
deployment = [0.3; 0.6; 0.9; 0.3; 0.6; 0.9];
response_axis = ["z"; "z"; "z"; "x"; "x"; "x"];
conditions = table(curve_id, load_case, deployment, response_axis);
end


function ori = buildOrigami(row, deployment, plotOpen)
rho = 1200;
L = 0.2;

pattern = double(row.pattern);
m = double(row.m);
n = double(row.n);
tcrease = double(row.tcrease);
tpanel = double(row.tpanel);
W = double(row.W);
creaseE = double(row.creaseE);
panelE = double(row.panelE);

ori = OrigamiSolver;
ori.showNumber = 0;
ori.faceColorNumbering = 'yellow';
ori.faceAlphaNumbering = 1;

if pattern == 1
    gama = 70 * pi / 180;
    b = L / m;
    a = (L - b * cot(gama)) / n;
    [ori.node0, ori.panel0] = GenerateMiuraSheet(a, b, gama, m, n, deployment);
elseif pattern == 2
    b = L / m;
    a = L / n;
    [ori.node0, ori.panel0] = GenerateTMPSheet(a, b, m, n, deployment);
else
    error('Unsupported pattern value: %g', pattern);
end

ori.Mesh_AnalyzeOriginalPattern();
ori.viewAngle1 = 45;
ori.viewAngle2 = 45;
ori.displayRange = L;
ori.displayRangeRatio = 0.1;
ori.deformEdgeShow = 0;

if plotOpen
    ori.Plot_UnmeshedOrigami();
    close;
end

creaseIndex = ori.oldCreaseType ~= 1;
ori.creaseWidthVec = zeros(ori.oldCreaseNum, 1);
ori.creaseWidthVec(creaseIndex) = W;
ori.compliantCreaseOpen = 0;
ori.mesh2D3D = 3;
ori.Mesh_Mesh();

if plotOpen
    ori.Plot_MeshedOrigami();
    close;
end

ori.panelE = panelE;
ori.creaseE = creaseE;
ori.panelPoisson = 0.3;
ori.creasePoisson = 0.3;

panelNum = size(ori.panel0, 2);
ori.panelThickVec = tpanel * ones(panelNum, 1);
ori.panelW = W;

ori.creaseThickVec = zeros(ori.oldCreaseNum, 1);
ori.creaseThickVec(creaseIndex) = tcrease;

ori.densityCrease = rho;
ori.densityPanel = rho;
end


function curveTable = runLoadCase(ori, sampleId, curveId, loadCase, deployment, responseAxis, curvePoints, row, baseFinalLoad, finalLoadMode, targetLinearDisplacement, maxFinalLoad, plotOpen, requirePhysics)
nr = ControllerNRLoading;
nr.videoOpen = 0;
nr.plotOpen = plotOpen;
nr.increStep = curvePoints;
nr.tol = 1e-7;

xCoord = ori.newNode(:, 1);
tol = max(1e-10, 1e-8 * max(abs(xCoord)));
supNode = find(abs(xCoord - min(xCoord)) <= tol);
forceNode = find(abs(xCoord - max(xCoord)) <= tol);
if isempty(supNode) || isempty(forceNode)
    error('Could not identify support or loading nodes.');
end
if ~isempty(intersect(supNode, forceNode))
    error('Support and force nodes overlap; structure is too narrow in x for this loading setup.');
end

nr.supp = [supNode, ones(length(supNode), 3)];
referenceStiffness = getReferenceStiffness(row, curveId);
if finalLoadMode == "stiffness_scaled"
    finalLoad = referenceStiffness * targetLinearDisplacement;
    finalLoad = min(finalLoad, maxFinalLoad);
else
    finalLoad = baseFinalLoad;
end
unitForce = (finalLoad / curvePoints) / length(forceNode);
loadComponents = zeros(length(forceNode), 3);

if loadCase == "bending"
    axisIndex = 3;
    loadComponents(:, axisIndex) = -unitForce;
elseif loadCase == "axial"
    axisIndex = 1;
    loadComponents(:, axisIndex) = unitForce;
else
    error('Unsupported load case: %s', loadCase);
end

nr.load = [forceNode, loadComponents];
ori.loadingController{1} = {"NR", nr};
ori.Solver_Solve();

availableSteps = min(curvePoints, size(nr.Uhis, 1));
step = (1:curvePoints)';
displacement = nan(curvePoints, 1);
signed_displacement = nan(curvePoints, 1);

u = nr.Uhis(1:availableSteps, forceNode, axisIndex);
displacement(1:availableSteps) = reshape(mean(abs(u), 2), [], 1);
signed_displacement(1:availableSteps) = reshape(mean(u, 2), [], 1);

forcePerStep = sum(abs(nr.load(:, axisIndex + 1)));
signedForcePerStep = sum(nr.load(:, axisIndex + 1));
force = step * forcePerStep;
signed_force = step * signedForcePerStep;
converged = isfinite(displacement);

energyHistory = historyMatrix(nr, 'strainEnergyHis', curvePoints, 4, requirePhysics);
% SWOMPS ControllerNRLoading.strainEnergyHis stores four energy channels in
% the local OrigamiSimulator version used for this dataset. Columns 1 and 4
% are crease/spring-related energies; columns 2 and 3 are panel/bar-related
% energies. Keep this mapping explicit because a solver-side column order
% change would otherwise silently corrupt the physical summary labels.
strain_energy_crease = energyHistory(:, 1) + energyHistory(:, 4);
strain_energy_panel = energyHistory(:, 2) + energyHistory(:, 3);
strain_energy_total = strain_energy_crease + strain_energy_panel;
max_bar_stress = maxAbsHistory(nr, 'barSxHis', curvePoints, requirePhysics);
max_bar_strain = maxAbsHistory(nr, 'barExHis', curvePoints, requirePhysics);
max_crease_moment = maxAbsHistory(nr, 'sprMHis', curvePoints, requirePhysics);
max_crease_rotation = maxAbsHistory(nr, 'sprRotHis', curvePoints, requirePhysics);

sample_id = repmat(sampleId, curvePoints, 1);
curve_id = repmat(curveId, curvePoints, 1);
load_case = repmat(loadCase, curvePoints, 1);
deployment_col = repmat(deployment, curvePoints, 1);
response_axis = repmat(responseAxis, curvePoints, 1);
final_load = repmat(finalLoad, curvePoints, 1);
reference_stiffness = repmat(referenceStiffness, curvePoints, 1);
target_linear_displacement = repmat(targetLinearDisplacement, curvePoints, 1);

curveTable = table( ...
    sample_id, curve_id, load_case, deployment_col, response_axis, step, ...
    force, displacement, signed_force, signed_displacement, converged, ...
    strain_energy_total, strain_energy_crease, strain_energy_panel, ...
    max_bar_stress, max_bar_strain, max_crease_moment, max_crease_rotation, ...
    final_load, reference_stiffness, target_linear_displacement, ...
    'VariableNames', { ...
        'sample_id', 'curve_id', 'load_case', 'deployment', 'response_axis', 'step', ...
        'force', 'displacement', 'signed_force', 'signed_displacement', 'converged', ...
        'strain_energy_total', 'strain_energy_crease', 'strain_energy_panel', ...
        'max_bar_stress', 'max_bar_strain', 'max_crease_moment', 'max_crease_rotation', ...
        'final_load', 'reference_stiffness', 'target_linear_displacement'});
end


function history = historyMatrix(controller, propertyName, curvePoints, minColumns, requirePhysics)
history = nan(curvePoints, minColumns);
if ~isprop(controller, propertyName)
    if requirePhysics
        error('Required SWOMPS history %s is not available on ControllerNRLoading.', propertyName);
    end
    return;
end
rawHistory = controller.(propertyName);
if isempty(rawHistory)
    if requirePhysics
        error('Required SWOMPS history %s is empty.', propertyName);
    end
    return;
end
if requirePhysics
    if size(rawHistory, 1) < curvePoints
        error('Required SWOMPS history %s has %d rows, expected %d.', propertyName, size(rawHistory, 1), curvePoints);
    end
    if size(rawHistory, 2) < minColumns
        error('Required SWOMPS history %s has %d columns, expected at least %d.', propertyName, size(rawHistory, 2), minColumns);
    end
    requiredHistory = rawHistory(1:curvePoints, 1:minColumns);
    if any(~isfinite(requiredHistory(:)))
        error('Required SWOMPS history %s contains NaN or Inf.', propertyName);
    end
end
availableRows = min(curvePoints, size(rawHistory, 1));
availableColumns = min(size(rawHistory, 2), minColumns);
history(1:availableRows, 1:availableColumns) = rawHistory(1:availableRows, 1:availableColumns);
end


function values = maxAbsHistory(controller, propertyName, curvePoints, requirePhysics)
values = nan(curvePoints, 1);
if ~isprop(controller, propertyName)
    if requirePhysics
        error('Required SWOMPS history %s is not available on ControllerNRLoading.', propertyName);
    end
    return;
end
rawHistory = controller.(propertyName);
if isempty(rawHistory)
    if requirePhysics
        error('Required SWOMPS history %s is empty.', propertyName);
    end
    return;
end
if requirePhysics
    if size(rawHistory, 1) < curvePoints
        error('Required SWOMPS history %s has %d rows, expected %d.', propertyName, size(rawHistory, 1), curvePoints);
    end
    requiredHistory = rawHistory(1:curvePoints, :);
    if any(~isfinite(requiredHistory(:)))
        error('Required SWOMPS history %s contains NaN or Inf.', propertyName);
    end
end
availableRows = min(curvePoints, size(rawHistory, 1));
values(1:availableRows) = max(abs(rawHistory(1:availableRows, :)), [], 2);
end


function referenceStiffness = getReferenceStiffness(row, curveId)
stiffnessColumns = { ...
    'bendstiff30', 'bendstiff60', 'bendstiff90', ...
    'axialstiff30', 'axialstiff60', 'axialstiff90'};
if curveId < 0 || curveId >= numel(stiffnessColumns)
    error('Unsupported curve id for stiffness lookup: %g', curveId);
end
columnName = stiffnessColumns{curveId + 1};
if ~ismember(columnName, row.Properties.VariableNames)
    error('Missing stiffness column for scaled loading: %s', columnName);
end
referenceStiffness = double(row.(columnName));
if referenceStiffness <= 0 || ~isfinite(referenceStiffness)
    error('Invalid reference stiffness for %s: %.12g', columnName, referenceStiffness);
end
end


function logFailure(outputDir, sampleId, rowIndex, ME)
logPath = fullfile(outputDir, 'failures.log');
fid = fopen(logPath, 'a');
if fid < 0
    return;
end
cleanup = onCleanup(@() fclose(fid));
fprintf(fid, '[%s] row=%d sample_id=%s\n', datestr(now, 31), rowIndex, sampleId);
fprintf(fid, '%s\n', ME.message);
for k = 1:numel(ME.stack)
    fprintf(fid, '  at %s:%d\n', ME.stack(k).name, ME.stack(k).line);
end
fprintf(fid, '\n');
end
