classdef TestMeshConvergence < matlab.unittest.TestCase
%TESTMESHCONVERGENCE Tests deterministic mesh-convergence measurements.

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
        function testIdenticalMeshesHaveZeroChange(testCase)
            mesh = TestMeshConvergence.tetrahedronFixture();

            metrics = compare_mesh_convergence(mesh, mesh);

            testCase.verifyEqual(metrics.bidirectional_max_mm, 0, ...
                'AbsTol', eps);
            testCase.verifyEqual(metrics.bidirectional_rms_mm, 0, ...
                'AbsTol', eps);
            testCase.verifyEqual(metrics.relative_area_change, 0, ...
                'AbsTol', eps);
            testCase.verifyEqual(metrics.relative_volume_change, 0, ...
                'AbsTol', eps);
            testCase.verifyEqual(metrics.component_count_a, 1);
            testCase.verifyEqual(metrics.component_count_b, 1);
            testCase.verifyTrue(metrics.topology_stable);
        end

        function testTranslationHasKnownVertexDistanceProxy(testCase)
            first = TestMeshConvergence.tetrahedronFixture();
            second = first;
            second.vertices = second.vertices + [10, 0, 0];

            metrics = compare_mesh_convergence(first, second);

            testCase.verifyEqual(metrics.directed_a_to_b_max_mm, 10, ...
                'AbsTol', 100 * eps);
            testCase.verifyEqual(metrics.directed_b_to_a_max_mm, 10, ...
                'AbsTol', 100 * eps);
            testCase.verifyEqual(metrics.bidirectional_max_mm, 10, ...
                'AbsTol', 100 * eps);
            testCase.verifyEqual(metrics.relative_area_change, 0, ...
                'AbsTol', 100 * eps);
            testCase.verifyEqual(metrics.relative_volume_change, 0, ...
                'AbsTol', 100 * eps);
        end

        function testUniformScalingChangesAreaAndVolume(testCase)
            first = TestMeshConvergence.tetrahedronFixture();
            second = first;
            second.vertices = 2 .* second.vertices;

            metrics = compare_mesh_convergence(first, second);

            testCase.verifyEqual(metrics.area_b_mm2, ...
                4 .* metrics.area_a_mm2, 'RelTol', 100 * eps);
            testCase.verifyEqual(metrics.volume_b_mm3, ...
                8 .* metrics.volume_a_mm3, 'RelTol', 100 * eps);
            testCase.verifyEqual(metrics.relative_area_change, 3, ...
                'RelTol', 100 * eps);
            testCase.verifyEqual(metrics.relative_volume_change, 7, ...
                'RelTol', 100 * eps);
            testCase.verifyTrue(metrics.topology_stable);
        end

        function testClosedAndOpenMeshesAreNotTopologyStable(testCase)
            closed = TestMeshConvergence.tetrahedronFixture();
            open = closed;
            open.faces(end, :) = [];

            metrics = compare_mesh_convergence(closed, open);

            testCase.verifyFalse(metrics.topology_stable);
            testCase.verifyEqual(metrics.boundary_edge_count_a, 0);
            testCase.verifyGreaterThan(metrics.boundary_edge_count_b, 0);
            testCase.verifyNotEqual( ...
                metrics.euler_characteristic_a, ...
                metrics.euler_characteristic_b);
        end

        function testAllMethodsProduceDeterministicSmokeEvidence(testCase)
            cases = { ...
                'M1', [0.0700794, 0.1246504, 0.0693255, 0]; ...
                'M2', [0.099, 0.099, 0.099, 7.501]; ...
                'M3', [0.171, 0.142, 0.115, 4.577]};
            for caseIndex = 1:size(cases, 1)
                values = cases{caseIndex, 2};
                projected = project_method_constraints( ...
                    cases{caseIndex, 1}, struct( ...
                    'c0', values(1), 'c1', values(2), ...
                    'c2', values(3), 'w', values(4)), testCase.Config);
                coarseField = build_finite_csg_field( ...
                    projected, testCase.Config, 12, false);
                fineField = build_finite_csg_field( ...
                    projected, testCase.Config, 16, false);
                coarseMesh = extract_isosurface_mesh(coarseField, 0);
                fineMesh = extract_isosurface_mesh(fineField, 0);

                first = compare_mesh_convergence(coarseMesh, fineMesh);
                second = compare_mesh_convergence(coarseMesh, fineMesh);

                testCase.verifyEqual(first, second);
                testCase.verifyGreaterThanOrEqual( ...
                    first.component_count_a, 1);
                testCase.verifyGreaterThanOrEqual( ...
                    first.component_count_b, 1);
                testCase.verifyClass(first.topology_stable, 'logical');
                testCase.verifyLessThanOrEqual(first.sample_count_a, 5000);
                testCase.verifyLessThanOrEqual(first.sample_count_b, 5000);
            end
        end

        function testProductionEvidenceLevelsRemainExplicit(testCase)
            testCase.verifyEqual( ...
                testCase.Config.method_bounds.M1.levels, [96; 128; 160]);
            testCase.verifyEqual( ...
                testCase.Config.method_bounds.M2.levels, [96; 128; 160]);
            testCase.verifyEqual( ...
                testCase.Config.method_bounds.M3.levels, ...
                [96; 128; 160; 192]);
        end
    end

    methods (Static, Access = private)
        function mesh = tetrahedronFixture()
            mesh.vertices = [0 0 0;1 0 0;0 1 0;0 0 1];
            mesh.faces = [1 3 2;1 2 4;2 3 4;3 1 4];
        end
    end
end
