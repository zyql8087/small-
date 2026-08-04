classdef TestSurfaceMesh < matlab.unittest.TestCase
%TESTSURFACEMESH Tests continuous-field surface extraction and mesh gates.

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
        function testIsosurfacePreservesPhysicalCoordinateOrder(testCase)
            field = struct();
            field.x_mm = -0.1:0.1:1.1;
            field.y_mm = -0.1:0.1:2.1;
            field.z_mm = -0.1:0.1:0.9;
            [X, ~, ~] = ndgrid( ...
                field.x_mm, field.y_mm, field.z_mm);
            field.F = X - 0.35;

            mesh = extract_isosurface_mesh(field, 0);

            testCase.verifyEqual(mesh.vertices(:, 1), ...
                0.35 * ones(size(mesh.vertices, 1), 1), ...
                'AbsTol', 1e-12);
            testCase.verifyGreaterThan(range(mesh.vertices(:, 2)), 1.9);
            testCase.verifyGreaterThan(range(mesh.vertices(:, 3)), 0.8);
        end

        function testRealCsgMeshUsesConfiguredPhysicalBounds(testCase)
            raw = struct('c0', 0.10, 'c1', 0.10, ...
                'c2', 0.10, 'w', 0);
            projected = project_method_constraints( ...
                'M1', raw, testCase.Config);
            field = build_finite_csg_field( ...
                projected, testCase.Config, 16, false);

            mesh = extract_isosurface_mesh(field, 0);

            testCase.verifyTrue(all(isfinite(mesh.vertices(:))));
            testCase.verifyGreaterThan(size(mesh.faces, 1), 0);
            testCase.verifyGreaterThanOrEqual( ...
                min(mesh.vertices(:, 1)), -10 * eps);
            testCase.verifyLessThanOrEqual( ...
                max(mesh.vertices(:, 1)), 1 + 10 * eps);
            testCase.verifyGreaterThanOrEqual( ...
                min(mesh.vertices(:, 3)), -10 * eps);
            testCase.verifyLessThanOrEqual( ...
                max(mesh.vertices(:, 3)), 2 + 10 * eps);
        end

        function testMismatchedFieldDimensionsRejected(testCase)
            field = struct('x_mm', 0:1, 'y_mm', 0:1, ...
                'z_mm', 0:1, 'F', zeros(3, 2, 2));
            testCase.verifyError(@() extract_isosurface_mesh(field, 0), ...
                'MATLABGyroid:InvalidGeometry');
        end

        function testEmptyIsosurfaceRejected(testCase)
            field = struct('x_mm', 0:1, 'y_mm', 0:1, ...
                'z_mm', 0:1, 'F', ones(2, 2, 2));
            testCase.verifyError(@() extract_isosurface_mesh(field, 0), ...
                'MATLABGyroid:EmptyMesh');
        end
    end
end
