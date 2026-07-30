classdef TestFieldKernel < matlab.unittest.TestCase
%TESTFIELDKERNEL Tests the projected-parameter and implicit-field kernel.

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
                testCase.BaseDir, 'configs', 'compiler_config.example.json'));
        end
    end

    methods (Test)
        function testM1PassesThresholdControlsAndRequiresZeroW(testCase)
            raw = struct('c0', 0.04, 'c1', 0.10, 'c2', 0.20, 'w', 0);
            projected = project_method_constraints('M1', raw, testCase.Config);

            testCase.verifyEqual( ...
                [projected.c0, projected.c1, projected.c2, projected.w], ...
                [0.04, 0.10, 0.20, 0]);
            testCase.verifyFalse(projected.projection_applied);
            testCase.verifyEqual(projected.projection_l2, 0);
            testCase.verifyTrue(isnan(projected.c_projected));

            raw.w = 4;
            TestFieldKernel.verifyFailure(testCase, ...
                @() project_method_constraints('M1', raw, testCase.Config), ...
                'MATLABGyroid:MethodConstraint', 'M1 requires w=0');
        end

        function testM2UsesOrthogonalMeanProjection(testCase)
            raw = struct('c0', 0.04, 'c1', 0.10, 'c2', 0.16, 'w', 4);
            projected = project_method_constraints('M2', raw, testCase.Config);

            testCase.verifyEqual( ...
                [projected.c0, projected.c1, projected.c2, ...
                projected.c_projected], [0.10, 0.10, 0.10, 0.10], ...
                'AbsTol', 10 * eps);
            testCase.verifyEqual(projected.w, 4);
            testCase.verifyEqual(projected.projection_l2, ...
                norm([-0.06, 0, 0.06]), 'AbsTol', 10 * eps);
            testCase.verifyTrue(projected.projection_applied);
            testCase.verifyEqual(projected.raw_parameters, raw);
        end

        function testM2EqualControlsRecordNoProjectionChange(testCase)
            raw = struct('c0', 0.10, 'c1', 0.10, 'c2', 0.10, 'w', 4);
            projected = project_method_constraints('M2', raw, testCase.Config);

            testCase.verifyFalse(projected.projection_applied);
            testCase.verifyEqual(projected.projection_l2, 0, ...
                'AbsTol', 10 * eps);
        end

        function testM3PassesAllControls(testCase)
            raw = struct('c0', 0.03, 'c1', 0.10, 'c2', 0.20, 'w', 4);
            projected = project_method_constraints('M3', raw, testCase.Config);

            testCase.verifyEqual( ...
                [projected.c0, projected.c1, projected.c2, projected.w], ...
                [0.03, 0.10, 0.20, 4]);
            testCase.verifyFalse(projected.projection_applied);
            testCase.verifyEqual(projected.projection_l2, 0);
            testCase.verifyTrue(isnan(projected.c_projected));
        end

        function testUnknownMethodRejected(testCase)
            raw = struct('c0', 0.10, 'c1', 0.10, 'c2', 0.10, 'w', 0);
            TestFieldKernel.verifyFailure(testCase, ...
                @() project_method_constraints('M4', raw, testCase.Config), ...
                'MATLABGyroid:InvalidRequest', 'method must be one of');
        end

        function testMethodMustBeTextScalar(testCase)
            raw = struct('c0', 0.10, 'c1', 0.10, 'c2', 0.10, 'w', 0);
            TestFieldKernel.verifyFailure(testCase, ...
                @() project_method_constraints(struct('bad', true), raw, ...
                testCase.Config), 'MATLABGyroid:InvalidRequest', ...
                'method must be a character row vector or string scalar');
        end

        function testMissingParameterRejected(testCase)
            raw = struct('c0', 0.10, 'c1', 0.10, 'c2', 0.10);
            TestFieldKernel.verifyFailure(testCase, ...
                @() project_method_constraints('M1', raw, testCase.Config), ...
                'MATLABGyroid:InvalidRequest', ...
                'parameters must have fields {c0, c1, c2, w}');
        end

        function testExtraParameterRejected(testCase)
            raw = struct('c0', 0.10, 'c1', 0.10, 'c2', 0.10, ...
                'w', 0, 'unused', 1);
            TestFieldKernel.verifyFailure(testCase, ...
                @() project_method_constraints('M1', raw, testCase.Config), ...
                'MATLABGyroid:InvalidRequest', ...
                'parameters must have fields {c0, c1, c2, w}');
        end

        function testStructArrayParametersRejected(testCase)
            raw = repmat( ...
                struct('c0', 0.10, 'c1', 0.10, 'c2', 0.10, 'w', 0), ...
                1, 2);
            TestFieldKernel.verifyFailure(testCase, ...
                @() project_method_constraints('M1', raw, testCase.Config), ...
                'MATLABGyroid:InvalidRequest', ...
                'parameters must be a scalar struct');
        end

        function testNonFiniteAndNonScalarControlsRejected(testCase)
            cases = { ...
                struct('c0', NaN, 'c1', 0.10, 'c2', 0.10, 'w', 0), 'c0'; ...
                struct('c0', 0.10, 'c1', Inf, 'c2', 0.10, 'w', 0), 'c1'; ...
                struct('c0', 0.10, 'c1', 0.10, 'c2', [0.1, 0.2], 'w', 0), 'c2'; ...
                struct('c0', 0.10, 'c1', 0.10, 'c2', 0.10, 'w', 1i), 'w'};
            for caseIndex = 1:size(cases, 1)
                TestFieldKernel.verifyFailure(testCase, ...
                    @() project_method_constraints('M1', cases{caseIndex, 1}, ...
                    testCase.Config), 'MATLABGyroid:InvalidRequest', ...
                    sprintf('parameters.%s must be a finite real numeric scalar', ...
                    cases{caseIndex, 2}));
            end
        end

        function testM1ClosedThresholdBoundsEnforced(testCase)
            atBounds = struct('c0', 0.03, 'c1', 0.10, 'c2', 0.20, 'w', 0);
            project_method_constraints('M1', atBounds, testCase.Config);

            atBounds.c0 = 0.03 - 1e-6;
            TestFieldKernel.verifyFailure(testCase, ...
                @() project_method_constraints('M1', atBounds, testCase.Config), ...
                'MATLABGyroid:OutOfBounds', 'M1.c0');
            atBounds.c0 = 0.03;
            atBounds.c2 = 0.20 + 1e-6;
            TestFieldKernel.verifyFailure(testCase, ...
                @() project_method_constraints('M1', atBounds, testCase.Config), ...
                'MATLABGyroid:OutOfBounds', 'M1.c2');
        end

        function testM2ProjectedThresholdBoundEnforced(testCase)
            raw = struct('c0', 0.01, 'c1', 0.01, 'c2', 0.01, 'w', 4);
            TestFieldKernel.verifyFailure(testCase, ...
                @() project_method_constraints('M2', raw, testCase.Config), ...
                'MATLABGyroid:OutOfBounds', 'M2.c_projected');
        end

        function testOpenWEndpointsRejectedForM2AndM3(testCase)
            for method = {'M2', 'M3'}
                raw = struct('c0', 0.10, 'c1', 0.10, 'c2', 0.10, 'w', 2);
                TestFieldKernel.verifyFailure(testCase, ...
                    @() project_method_constraints(method{1}, raw, testCase.Config), ...
                    'MATLABGyroid:OutOfBounds', sprintf('%s.w', method{1}));
                raw.w = 8;
                TestFieldKernel.verifyFailure(testCase, ...
                    @() project_method_constraints(method{1}, raw, testCase.Config), ...
                    'MATLABGyroid:OutOfBounds', sprintf('%s.w', method{1}));
            end
        end
    end

    methods (Static, Access = private)
        function verifyFailure(testCase, action, expectedId, messageFragment)
            caughtException = [];
            try
                action();
            catch caught
                caughtException = caught;
            end
            testCase.assertNotEmpty(caughtException, ...
                sprintf('Expected %s containing "%s".', ...
                expectedId, messageFragment));
            testCase.verifyEqual(caughtException.identifier, expectedId);
            testCase.verifyTrue(contains(caughtException.message, messageFragment), ...
                sprintf('Actual message: %s', caughtException.message));
        end
    end
end
