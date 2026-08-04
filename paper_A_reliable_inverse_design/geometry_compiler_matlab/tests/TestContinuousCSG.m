classdef TestContinuousCSG < matlab.unittest.TestCase
%TESTCONTINUOUSCSG Tests the finite continuous hard-box CSG field.

    properties (Access = private)
        BaseDir
        Config
    end

    methods (TestClassSetup)
        function setupClass(testCase)
            testFile = mfilename('fullpath');
            testCase.BaseDir = fileparts(fileparts(testFile));
            addpath(fullfile(testCase.BaseDir, 'core'));
            testCase.Config = load_compiler_config(fullfile( ...
                testCase.BaseDir, 'configs', ...
                'compiler_config.example.json'));
        end
    end

    methods (Test)
        function testHardBoxCsgTruthTable(testCase)
            fSheet = reshape([-1, -1, 1, 1], 2, 2);
            fBox = reshape([-1, 1, -1, 1], 2, 2);

            F = compose_hard_box_csg(fSheet, fBox, 1.0);

            testCase.verifyEqual(F <= 0, ...
                (fSheet <= 0) & (fBox <= 0));
            testCase.verifyEqual(F, max(fSheet, fBox));
        end

        function testFiniteGridIsHalfStepStaggered(testCase)
            projected = TestContinuousCSG.projectExample( ...
                testCase, 'M1', [0.10, 0.10, 0.10, 0]);

            field = build_finite_csg_field( ...
                projected, testCase.Config, 8, false);

            h = 1 / 8;
            testCase.verifyEqual(field.x_over_l([1, end]), ...
                [-h / 2, 1 + h / 2], 'AbsTol', eps);
            testCase.verifyEqual(field.z_over_l([1, end]), ...
                [-h / 2, 2 + h / 2], 'AbsTol', eps);
            testCase.verifyFalse(any( ...
                field.x_over_l == 0 | field.x_over_l == 1));
            testCase.verifyTrue(all( ...
                field.F([1, end], :, :) > 0, 'all'));
            testCase.verifyTrue(all( ...
                field.F(:, [1, end], :) > 0, 'all'));
            testCase.verifyTrue(all( ...
                field.F(:, :, [1, end]) > 0, 'all'));
            testCase.verifyEqual(field.spacing_mm, ...
                testCase.Config.reference_length_mm / 8, 'AbsTol', eps);
            testCase.verifyEqual(field.exterior_margin_mm, ...
                testCase.Config.reference_length_mm / 16, 'AbsTol', eps);
        end

        function testProductionLevelEnforcement(testCase)
            projected = TestContinuousCSG.projectExample( ...
                testCase, 'M1', [0.10, 0.10, 0.10, 0]);

            testCase.verifyError(@() build_finite_csg_field( ...
                projected, testCase.Config, 8, true), ...
                'MATLABGyroid:InvalidGeometry');
            allowed = build_finite_csg_field( ...
                projected, testCase.Config, 96, true);
            testCase.verifyEqual(allowed.resolution, 96);
        end

        function testAllMethodsAreFiniteMixedAndDeterministic(testCase)
            cases = { ...
                'M1', [0.04, 0.10, 0.16, 0]; ...
                'M2', [0.04, 0.10, 0.16, 4]; ...
                'M3', [0.04, 0.10, 0.16, 4]};
            for caseIndex = 1:size(cases, 1)
                projected = TestContinuousCSG.projectExample(testCase, ...
                    cases{caseIndex, 1}, cases{caseIndex, 2});
                first = build_finite_csg_field( ...
                    projected, testCase.Config, 16, false);
                second = build_finite_csg_field( ...
                    projected, testCase.Config, 16, false);
                testCase.verifyTrue(all(isfinite(first.F(:))));
                testCase.verifyGreaterThan(first.interior_solid_count, 0);
                testCase.verifyGreaterThan(first.interior_void_count, 0);
                testCase.verifyEqual(first.solid_connectivity, 26);
                testCase.verifyGreaterThanOrEqual( ...
                    first.solid_component_count, 1);
                testCase.verifyEqual(first.solid_component_count, ...
                    second.solid_component_count);
                testCase.verifyEqual(first.F, second.F);
                testCase.verifyEqual(first.method, cases{caseIndex, 1});
                testCase.verifyEqual(first.geometry_definition, ...
                    'continuous_sheet_gyroid_intersect_hard_box');
            end
        end

        function testInvalidCsgInputsRejected(testCase)
            testCase.verifyError(@() compose_hard_box_csg( ...
                zeros(2), zeros(3), 1), ...
                'MATLABGyroid:InvalidGeometry');
            testCase.verifyError(@() compose_hard_box_csg( ...
                zeros(2), zeros(2), 0), ...
                'MATLABGyroid:InvalidGeometry');
            testCase.verifyError(@() compose_hard_box_csg( ...
                zeros(2), [0, NaN; 0, 0], 1), ...
                'MATLABGyroid:InvalidGeometry');
        end
    end

    methods (Static, Access = private)
        function projected = projectExample(testCase, method, values)
            raw = struct('c0', values(1), 'c1', values(2), ...
                'c2', values(3), 'w', values(4));
            projected = project_method_constraints( ...
                method, raw, testCase.Config);
        end
    end
end
