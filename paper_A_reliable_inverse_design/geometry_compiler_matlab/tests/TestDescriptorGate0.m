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
    end
end
