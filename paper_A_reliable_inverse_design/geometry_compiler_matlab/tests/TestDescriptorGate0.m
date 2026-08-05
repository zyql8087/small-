classdef TestDescriptorGate0 < matlab.unittest.TestCase
%TESTDESCRIPTORGATE0 Tests authenticated Small selection and later Gate-0 steps.

    properties (Access = private)
        BaseDir
        Config
    end

    methods (TestClassSetup)
        function setupClass(testCase)
            testCase.BaseDir = fileparts(fileparts(mfilename('fullpath')));
            addpath(testCase.BaseDir);
            addpath(fullfile(testCase.BaseDir, 'core'));
            gatePath = fullfile(testCase.BaseDir, 'gate0');
            if exist(gatePath, 'dir') == 7
                addpath(gatePath);
            end
            testCase.Config = load_compiler_config(fullfile( ...
                testCase.BaseDir, 'configs', 'compiler_config.example.json'));
        end
    end

    methods (Test)
        function testSelectsDeterministicDisjointSixPlusThirty(testCase)
            workbookHash = repmat('a', 1, 64);
            sheets = TestDescriptorGate0.syntheticSheets();
            selection = select_small_gate0_rows(sheets, workbookHash, ...
                testCase.Config);

            testCase.verifyEqual(numel(selection.rows), 36);
            methods = string({selection.rows.method});
            for method = ["M1", "M2", "M3"]
                rows = selection.rows(methods == method);
                testCase.verifyEqual(numel(rows), 12);
                testCase.verifyEqual(sum(strcmp({rows.role}, 'discovery')), 2);
                testCase.verifyEqual(sum(strcmp({rows.role}, 'confirmation')), 10);
            end
            ids = string({selection.rows.row_id});
            testCase.verifyEqual(numel(unique(ids)), 36);
            testCase.verifyEqual(selection.rows(1).selection_digest, ...
                sha256_text(sprintf('%s|%s|%d|M04-v2-selection', ...
                workbookHash, selection.rows(1).sheet, ...
                selection.rows(1).excel_row)));
        end

        function testRejectsInvalidHeaderAndIneligibleRows(testCase)
            sheets = TestDescriptorGate0.syntheticSheets();
            sheets(1).raw{1, 1} = 'wrong';
            testCase.verifyError(@() select_small_gate0_rows(sheets, ...
                repmat('a', 1, 64), testCase.Config), ...
                'MATLABGyroid:Gate0SelectionInvalid');

            sheets = TestDescriptorGate0.syntheticSheets();
            sheets(2).raw{2, 4} = 0;
            testCase.verifyError(@() select_small_gate0_rows(sheets, ...
                repmat('a', 1, 64), testCase.Config), ...
                'MATLABGyroid:Gate0SelectionInvalid');
        end

        function testSelectionIdentityBindsParametersAndArchivedTargets(testCase)
            workbookHash = repmat('a', 1, 64);
            baselineSheets = TestDescriptorGate0.syntheticSheets();
            baseline = select_small_gate0_rows(baselineSheets, ...
                workbookHash, testCase.Config);

            parameterSheets = baselineSheets;
            parameterSheets(1).raw{2, 1} = ...
                parameterSheets(1).raw{2, 1} + 0.0001;
            parameterChanged = select_small_gate0_rows(parameterSheets, ...
                workbookHash, testCase.Config);

            targetSheets = baselineSheets;
            targetSheets(1).raw{2, 9} = targetSheets(1).raw{2, 9} + 0.0001;
            targetChanged = select_small_gate0_rows(targetSheets, ...
                workbookHash, testCase.Config);

            testCase.verifyNotEqual(parameterChanged.selection_sha256, ...
                baseline.selection_sha256);
            testCase.verifyNotEqual(targetChanged.selection_sha256, ...
                baseline.selection_sha256);
        end

        function testPublicSelectorRejectsUnauthenticatedWorkbook(testCase)
            fixture = tempname;
            fileId = fopen([fixture, '.xlsx'], 'w');
            testCase.assertNotEqual(fileId, -1);
            fclose(fileId);
            cleanup = onCleanup(@() TestDescriptorGate0.deleteIfExists( ...
                [fixture, '.xlsx']));
            output = [fixture, '.json'];

            testCase.verifyError(@() prepare_small_gate0_selection( ...
                [fixture, '.xlsx'], output), ...
                'MATLABGyroid:Gate0SelectionInvalid');
        end

        function testCalibrationSelectsPreregisteredDensityAndGlobalScale(testCase)
            selection = testCase.loadFrozenSelection();
            calibration = calibrate_legacy_scale(selection, ...
                @TestDescriptorGate0.fakeLegacy, 1e-12);

            testCase.verifyEqual(calibration.candidate_densities, ...
                [20, 24, 30, 32, 40, 48, 60, 64, 80, 96]);
            testCase.verifyEqual(calibration.status, ...
                'M04_CALIBRATION_IDENTIFIED');
            testCase.verifyEqual(calibration.samples_per_reference_length, 30);
            testCase.verifyEqual(calibration.reference_length_mm, 2, ...
                'AbsTol', 1e-12);
            testCase.verifyLessThanOrEqual(calibration.scale_statistics.mard, .02);
            testCase.verifyLessThanOrEqual(calibration.scale_statistics.p95, .05);
        end

        function testCalibrationReturnsNotIdentifiedForIneligibleDensity(testCase)
            selection = testCase.loadFrozenSelection();
            calibration = calibrate_legacy_scale(selection, ...
                @TestDescriptorGate0.fakeIneligibleLegacy, 1e-12);

            testCase.verifyEqual(calibration.status, ...
                'M04_SCALE_NOT_IDENTIFIED');
            testCase.verifyFalse(isfield(calibration, 'reference_length_mm'));
        end

        function testCalibrationAcceptsThresholdEqualityAndAllScaleLaws(testCase)
            selection = testCase.loadFrozenSelection();
            calibration = calibrate_legacy_scale(selection, ...
                @TestDescriptorGate0.fakeBoundaryLegacy, 1e-12);

            testCase.verifyEqual(calibration.status, ...
                'M04_CALIBRATION_IDENTIFIED');
            testCase.verifyEqual(calibration.samples_per_reference_length, 20);
            testCase.verifyTrue(calibration.density_results(1).eligible);
            testCase.verifyEqual(calibration.scale_statistics.estimates, ...
                2 * ones(6, 3), 'AbsTol', 1e-12);
        end

        function testCalibrationRejectsNonpositiveScaleAndGroupDisagreement(testCase)
            selection = testCase.loadFrozenSelection();
            nonpositive = calibrate_legacy_scale(selection, ...
                @TestDescriptorGate0.fakeNonpositiveLegacy, 1e-12);
            disagreement = calibrate_legacy_scale(selection, ...
                @TestDescriptorGate0.fakeGroupDisagreementLegacy, 1e-12);

            testCase.verifyEqual(nonpositive.status, ...
                'M04_SCALE_NOT_IDENTIFIED');
            testCase.verifyEqual(disagreement.status, ...
                'M04_SCALE_NOT_IDENTIFIED');
        end

        function testCalibrationRejectsSelectionValueTampering(testCase)
            selection = testCase.loadFrozenSelection();
            selection.rows(1).archived_descriptors.thickness = ...
                selection.rows(1).archived_descriptors.thickness + .01;

            testCase.verifyError(@() calibrate_legacy_scale(selection, ...
                @TestDescriptorGate0.fakeLegacy, 1e-12), ...
                'MATLABGyroid:M04Gate0NotFrozen');

            selection = testCase.loadFrozenSelection();
            selection.schema_version = '9.0';
            testCase.verifyError(@() calibrate_legacy_scale(selection, ...
                @TestDescriptorGate0.fakeLegacy, 1e-12), ...
                'MATLABGyroid:M04Gate0NotFrozen');

            selection = testCase.loadFrozenSelection();
            selection.rows(1).effective_parameters.c0 = ...
                selection.rows(1).effective_parameters.c0 + .01;
            testCase.verifyError(@() calibrate_legacy_scale(selection, ...
                @TestDescriptorGate0.fakeLegacy, 1e-12), ...
                'MATLABGyroid:M04Gate0NotFrozen');
        end

        function testCalibrationRejectsSelfConsistentWrongWorkbook(testCase)
            selection = testCase.loadFrozenSelection();
            selection.workbook_sha256 = repmat('a', 1, 64);
            for index = 1:numel(selection.rows)
                row = selection.rows(index);
                selection.rows(index).selection_digest = sha256_text(sprintf( ...
                    '%s|%s|%d|M04-v2-selection', ...
                    selection.workbook_sha256, row.sheet, row.excel_row));
            end
            selection.selection_canonical_text = ...
                canonical_small_gate0_selection(selection.workbook_sha256, ...
                selection.rows, testCase.Config);
            selection.selection_sha256 = sha256_text( ...
                selection.selection_canonical_text);

            testCase.verifyError(@() calibrate_legacy_scale(selection, ...
                @TestDescriptorGate0.fakeLegacy, 1e-12), ...
                'MATLABGyroid:M04Gate0NotFrozen');
        end

        function testCalibrationRejectsSelfConsistentSelectionMutation(testCase)
            selection = testCase.loadFrozenSelection();
            selection.rows(1).archived_descriptors.thickness = ...
                selection.rows(1).archived_descriptors.thickness + .01;
            selection.selection_canonical_text = ...
                canonical_small_gate0_selection(selection.workbook_sha256, ...
                selection.rows, testCase.Config);
            selection.selection_sha256 = sha256_text( ...
                selection.selection_canonical_text);

            testCase.verifyError(@() calibrate_legacy_scale(selection, ...
                @TestDescriptorGate0.fakeLegacy, 1e-12), ...
                'MATLABGyroid:M04Gate0NotFrozen');
        end

        function testFreezeRoundTripRejectsMutationAndOverwrite(testCase)
            selection = testCase.loadFrozenSelection();
            calibration = calibrate_legacy_scale(selection, ...
                @TestDescriptorGate0.fakeLegacy, 1e-12);
            fixture = tempname;
            mkdir(fixture);
            cleanup = onCleanup(@() rmdir(fixture, 's'));
            freezePath = fullfile(fixture, 'freeze.json');

            freeze = freeze_legacy_calibration( ...
                calibration, selection, freezePath);
            testCase.verifyFalse(isfield(freeze, 'freeze_canonical_text'));
            verified = verify_legacy_calibration_freeze(freezePath);
            testCase.verifyEqual(verified.freeze_sha256, freeze.freeze_sha256);
            testCase.verifyError(@() freeze_legacy_calibration( ...
                calibration, selection, freezePath), ...
                'MATLABGyroid:OutputConflict');

            tampered = jsondecode(fileread(freezePath));
            tampered.reference_length_mm = 3;
            TestDescriptorGate0.overwriteJson(freezePath, tampered);
            testCase.verifyError(@() verify_legacy_calibration_freeze(freezePath), ...
                'MATLABGyroid:M04Gate0NotFrozen');
        end

        function testFreezeRejectsScaleAndConfirmationOverrides(testCase)
            selection = testCase.loadFrozenSelection();
            calibration = calibrate_legacy_scale(selection, ...
                @TestDescriptorGate0.fakeLegacy, 1e-12);
            fixture = tempname;
            mkdir(fixture);
            cleanup = onCleanup(@() rmdir(fixture, 's'));

            scaleOverride = calibration;
            scaleOverride.reference_length_mm = 3;
            testCase.verifyError(@() freeze_legacy_calibration( ...
                scaleOverride, selection, fullfile(fixture, 'scale.json')), ...
                'MATLABGyroid:M04Gate0NotFrozen');

            rowOverride = calibration;
            rowOverride.confirmation_rows(1).selection_digest = repmat('0', 1, 64);
            testCase.verifyError(@() freeze_legacy_calibration( ...
                rowOverride, selection, fullfile(fixture, 'row.json')), ...
                'MATLABGyroid:M04Gate0NotFrozen');

            sourceOverride = calibration;
            sourceOverride.legacy_profile_sha256 = repmat('0', 1, 64);
            testCase.verifyError(@() freeze_legacy_calibration( ...
                sourceOverride, selection, fullfile(fixture, 'source.json')), ...
                'MATLABGyroid:M04Gate0NotFrozen');
        end

        function testFreezeVerifierRejectsSelfConsistentContractOverrides(testCase)
            selection = testCase.loadFrozenSelection();
            calibration = calibrate_legacy_scale(selection, ...
                @TestDescriptorGate0.fakeLegacy, 1e-12);
            fixture = tempname;
            mkdir(fixture);
            cleanup = onCleanup(@() rmdir(fixture, 's'));
            baselinePath = fullfile(fixture, 'baseline.json');
            freeze = freeze_legacy_calibration( ...
                calibration, selection, baselinePath);

            mutations = {
                'schema_version', '9.0'; ...
                'legacy_profile_sha256', repmat('0', 1, 64); ...
                'compiler_version', 'matlab-gyroid-9.9.9'; ...
                'tpms_designer_commit', repmat('a', 1, 40)};
            for index = 1:size(mutations, 1)
                tampered = freeze;
                tampered.(mutations{index, 1}) = mutations{index, 2};
                tampered.freeze_sha256 = sha256_text( ...
                    canonical_legacy_calibration_freeze(tampered));
                tamperedPath = fullfile(fixture, sprintf('tampered_%d.json', index));
                TestDescriptorGate0.overwriteJson(tamperedPath, tampered);
                testCase.verifyError(@() ...
                    verify_legacy_calibration_freeze(tamperedPath), ...
                    'MATLABGyroid:M04Gate0NotFrozen');
            end
        end


        function testFreezeVerifierRejectsSelfConsistentResultOverrides(testCase)
            selection = testCase.loadFrozenSelection();
            calibration = calibrate_legacy_scale(selection, ...
                @TestDescriptorGate0.fakeLegacy, 1e-12);
            fixture = tempname;
            mkdir(fixture);
            cleanup = onCleanup(@() rmdir(fixture, 's'));
            baselinePath = fullfile(fixture, 'baseline.json');
            freeze = freeze_legacy_calibration( ...
                calibration, selection, baselinePath);

            tampered = freeze;
            tampered.reference_length_mm = 3;
            tampered.reference_length_text = '3';
            testCase.verifySelfConsistentFreezeRejected( ...
                tampered, fixture, 'scale');

            tampered = freeze;
            tampered.thresholds.absolute_tolerance = 2e-12;
            testCase.verifySelfConsistentFreezeRejected( ...
                tampered, fixture, 'tolerance');

            tampered = freeze;
            tampered.confirmation_rows(1).row_id = 'class1:999';
            tampered.confirmation_rows(1).excel_row = 999;
            tampered.confirmation_rows(1).selection_digest = sha256_text( ...
                sprintf('%s|class1|999|M04-v2-selection', ...
                tampered.workbook_sha256));
            testCase.verifySelfConsistentFreezeRejected( ...
                tampered, fixture, 'identity');

            tampered = freeze;
            tampered.scale_statistics.maximum = 999;
            testCase.verifySelfConsistentFreezeRejected( ...
                tampered, fixture, 'statistics');

            tampered = freeze;
            tampered.extra_unsigned_field = 'forbidden';
            testCase.verifySelfConsistentFreezeRejected( ...
                tampered, fixture, 'extra_field');
        end
    end

    methods (Access = private)
        function selection = loadFrozenSelection(testCase)
            selection = jsondecode(fileread(fullfile(testCase.BaseDir, ...
                'tests', 'fixtures', 'small_gate0_rows.json')));
        end


        function verifySelfConsistentFreezeRejected(testCase, freeze, directory, name)
            freeze.freeze_sha256 = sha256_text( ...
                canonical_legacy_calibration_freeze(freeze));
            path = fullfile(directory, [name, '.json']);
            TestDescriptorGate0.overwriteJson(path, freeze);
            testCase.verifyError(@() verify_legacy_calibration_freeze(path), ...
                'MATLABGyroid:M04Gate0NotFrozen');
        end
    end

    methods (Static, Access = private)
        function sheets = syntheticSheets()
            headers = {'V1a','V1b','V1c','w','relativeVolume', ...
                'relativeArea','thickness','poreDiameter','areaMean'};
            names = {'class1', 'class2', 'class12'};
            methods = {'M1', 'M2', 'M3'};
            sheets = repmat(struct('name', '', 'method', '', 'raw', []), 3, 1);
            for sheetIndex = 1:3
                raw = cell(13, 9);
                raw(1, :) = headers;
                for rowIndex = 1:12
                    c = 0.04 + rowIndex / 1000;
                    switch methods{sheetIndex}
                        case 'M1'
                            parameter = [c, c + .001, c + .002, 0];
                        case 'M2'
                            parameter = [c, c, c, 3];
                        otherwise
                            parameter = [c, c + .001, c + .002, 3];
                    end
                    raw(rowIndex + 1, :) = num2cell([parameter, .3, .4, ...
                        .5 + rowIndex / 100, .6 + rowIndex / 100, ...
                        .7 + rowIndex / 100]);
                end
                sheets(sheetIndex).name = names{sheetIndex};
                sheets(sheetIndex).method = methods{sheetIndex};
                sheets(sheetIndex).raw = raw;
            end
        end

        function deleteIfExists(path)
            if exist(path, 'file') == 2
                delete(path);
            end
        end


        function result = fakeLegacy(row, density, referenceLength)
            densityError = .08;
            if density == 30
                densityError = .005;
            elseif density == 32
                densityError = .01;
            end
            archived = row.archived_descriptors;
            values = struct( ...
                'relativeVolume', archived.relativeVolume * (1 + densityError), ...
                'relativeArea', archived.relativeArea * (1 - densityError), ...
                'thickness', archived.thickness * referenceLength / 2, ...
                'poreDiameter', archived.poreDiameter * referenceLength / 2, ...
                'areaMean', archived.areaMean * referenceLength^2 / 4);
            result = struct('values', values);
        end

        function result = fakeIneligibleLegacy(row, ~, referenceLength)
            archived = row.archived_descriptors;
            values = struct( ...
                'relativeVolume', archived.relativeVolume * 1.2, ...
                'relativeArea', archived.relativeArea * .8, ...
                'thickness', archived.thickness * referenceLength / 2, ...
                'poreDiameter', archived.poreDiameter * referenceLength / 2, ...
                'areaMean', archived.areaMean * referenceLength^2 / 4);
            result = struct('values', values);
        end


        function result = fakeBoundaryLegacy(row, ~, referenceLength)
            archived = row.archived_descriptors;
            tolerance = 1e-12;
            values = struct( ...
                'relativeVolume', archived.relativeVolume + ...
                .02 * max(abs(archived.relativeVolume), tolerance), ...
                'relativeArea', archived.relativeArea - ...
                .02 * max(abs(archived.relativeArea), tolerance), ...
                'thickness', archived.thickness * referenceLength / 2, ...
                'poreDiameter', archived.poreDiameter * referenceLength / 2, ...
                'areaMean', archived.areaMean * referenceLength^2 / 4);
            result = struct('values', values);
        end


        function result = fakeNonpositiveLegacy(row, ~, ~)
            archived = row.archived_descriptors;
            values = struct('relativeVolume', archived.relativeVolume, ...
                'relativeArea', archived.relativeArea, ...
                'thickness', archived.thickness / 2, ...
                'poreDiameter', archived.poreDiameter / 2, ...
                'areaMean', -archived.areaMean / 4);
            result = struct('values', values);
        end


        function result = fakeGroupDisagreementLegacy(row, ~, ~)
            archived = row.archived_descriptors;
            values = struct('relativeVolume', archived.relativeVolume, ...
                'relativeArea', archived.relativeArea, ...
                'thickness', archived.thickness, ...
                'poreDiameter', archived.poreDiameter / 2, ...
                'areaMean', archived.areaMean / 9);
            result = struct('values', values);
        end

        function overwriteJson(path, value)
            fileId = fopen(path, 'w', 'n', 'UTF-8');
            assert(fileId ~= -1);
            cleanup = onCleanup(@() fclose(fileId));
            fprintf(fileId, '%s', jsonencode(value));
        end
    end
end
