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

        function testClosedTetrahedronPassesTopologyGate(testCase)
            mesh = TestSurfaceMesh.tetrahedronFixture();
            report = validate_surface_mesh( ...
                mesh, 0.1, TestSurfaceMesh.qcFixture());

            testCase.verifyTrue(report.valid);
            testCase.verifyEqual(report.failure_code, '');
            testCase.verifyEqual(report.boundary_edge_count, 0);
            testCase.verifyEqual(report.nonmanifold_edge_count, 0);
            testCase.verifyEqual(report.component_count, 1);
            testCase.verifyEqual(report.signed_volume_mm3, 1 / 6, ...
                'AbsTol', 100 * eps);
        end

        function testOpenMeshRejected(testCase)
            mesh = TestSurfaceMesh.tetrahedronFixture();
            mesh.faces(end, :) = [];
            report = validate_surface_mesh( ...
                mesh, 0.1, TestSurfaceMesh.qcFixture());

            testCase.verifyFalse(report.valid);
            testCase.verifyEqual(report.failure_code, 'OPEN_MESH');
            testCase.verifyGreaterThan(report.boundary_edge_count, 0);
        end

        function testDegenerateFaceRejected(testCase)
            mesh = TestSurfaceMesh.tetrahedronFixture();
            mesh.faces(1, :) = [1, 1, 2];
            report = validate_surface_mesh( ...
                mesh, 0.1, TestSurfaceMesh.qcFixture());

            testCase.verifyFalse(report.valid);
            testCase.verifyEqual(report.failure_code, 'DEGENERATE_MESH');
        end

        function testDuplicateFaceRejected(testCase)
            mesh = TestSurfaceMesh.tetrahedronFixture();
            mesh.faces(end + 1, :) = mesh.faces(1, :);
            report = validate_surface_mesh( ...
                mesh, 0.1, TestSurfaceMesh.qcFixture());

            testCase.verifyFalse(report.valid);
            testCase.verifyEqual(report.failure_code, 'DUPLICATE_FACE');
            testCase.verifyEqual(report.duplicate_face_count, 1);
        end

        function testNonmanifoldSharedEdgeRejected(testCase)
            first = TestSurfaceMesh.tetrahedronFixture();
            secondVertices = [0 0 0;1 0 0;0 -1 0;0 0 -1];
            secondFaces = [1 3 2;1 2 4;2 3 4;3 1 4];
            mesh.vertices = [first.vertices; secondVertices(3:4, :)];
            mesh.faces = [first.faces; remap_second(secondFaces)];
            report = validate_surface_mesh( ...
                mesh, 0.1, TestSurfaceMesh.qcFixture());

            testCase.verifyFalse(report.valid);
            testCase.verifyEqual(report.failure_code, 'NONMANIFOLD_MESH');
            testCase.verifyGreaterThan(report.nonmanifold_edge_count, 0);
        end

        function testDisconnectedClosedComponentsRejected(testCase)
            first = TestSurfaceMesh.tetrahedronFixture();
            mesh.vertices = [first.vertices; first.vertices + 3];
            mesh.faces = [first.faces; first.faces + 4];
            report = validate_surface_mesh( ...
                mesh, 0.1, TestSurfaceMesh.qcFixture());

            testCase.verifyFalse(report.valid);
            testCase.verifyEqual(report.failure_code, 'DISCONNECTED_SOLID');
            testCase.verifyEqual(report.component_count, 2);
        end

        function testLocallyInconsistentOrientationRejected(testCase)
            mesh = TestSurfaceMesh.tetrahedronFixture();
            mesh.faces(1, :) = mesh.faces(1, [1, 3, 2]);
            report = validate_surface_mesh( ...
                mesh, 0.1, TestSurfaceMesh.qcFixture());

            testCase.verifyFalse(report.valid);
            testCase.verifyEqual(report.failure_code, ...
                'INCONSISTENT_ORIENTATION');
        end

        function testCrossingTrianglesDetected(testCase)
            first = [0 0 0;1 0 0;0 1 0];
            second = [0.25 0.25 -1;0.25 0.25 1;0.75 0.25 0];
            testCase.verifyTrue(triangles_intersect_3d( ...
                first, second, 1e-12));
        end

        function testSeparatedTrianglesNotDetected(testCase)
            first = [0 0 0;1 0 0;0 1 0];
            second = [2 2 1;3 2 1;2 3 1];
            testCase.verifyFalse(triangles_intersect_3d( ...
                first, second, 1e-12));
        end

        function testCoplanarOverlapDetected(testCase)
            first = [0 0 0;1 0 0;0 1 0];
            second = [0.25 0.25 0;1.25 0.25 0;0.25 1.25 0];
            testCase.verifyTrue(triangles_intersect_3d( ...
                first, second, 1e-12));
        end

        function testCoplanarSeparatedTrianglesNotDetected(testCase)
            first = [0 0 0;1 0 0;0 1 0];
            second = [2 2 0;3 2 0;2 3 0];
            testCase.verifyFalse(triangles_intersect_3d( ...
                first, second, 1e-12));
        end

        function testAdjacentTetrahedronFacesAreIgnored(testCase)
            mesh = TestSurfaceMesh.tetrahedronFixture();
            pairs = detect_mesh_self_intersections(mesh, 1e-12);
            testCase.verifyEqual(pairs, zeros(0, 2));
        end

        function testPenetratingClosedComponentsRejectedAsSelfIntersection(testCase)
            first = TestSurfaceMesh.tetrahedronFixture();
            secondVertices = first.vertices + 0.2;
            mesh.vertices = [first.vertices; secondVertices];
            mesh.faces = [first.faces; first.faces + 4];
            qc = TestSurfaceMesh.qcFixture();
            qc.self_intersect_check = true;
            report = validate_surface_mesh(mesh, 0.1, qc);

            testCase.verifyFalse(report.valid);
            testCase.verifyEqual(report.failure_code, 'SELF_INTERSECTION');
            testCase.verifyGreaterThan( ...
                report.self_intersection_pair_count, 0);
        end

        function testClosedTetrahedronPassesSelfIntersectionCheck(testCase)
            mesh = TestSurfaceMesh.tetrahedronFixture();
            qc = TestSurfaceMesh.qcFixture();
            qc.self_intersect_check = true;
            report = validate_surface_mesh(mesh, 0.1, qc);

            testCase.verifyTrue(report.valid);
            testCase.verifyEqual(report.self_intersection_pair_count, 0);
        end
    end

    methods (Static, Access = private)
        function mesh = tetrahedronFixture()
            mesh.vertices = [0 0 0;1 0 0;0 1 0;0 0 1];
            mesh.faces = [1 3 2;1 2 4;2 3 4;3 1 4];
        end

        function qc = qcFixture()
            qc = struct('min_edge_length_ratio', 0.01, ...
                'self_intersect_check', false);
        end
    end
end

function faces = remap_second(faces)
    faces(faces == 3) = 5;
    faces(faces == 4) = 6;
end
