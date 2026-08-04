classdef TestCompilerPipeline < matlab.unittest.TestCase
%TESTCOMPILERPIPELINE Tests request parsing and compiler orchestration.

    properties (Access = private)
        BaseDir
        Config
    end

    methods (TestClassSetup)
        function setupClass(testCase)
            testFile = mfilename('fullpath');
            testCase.BaseDir = fileparts(fileparts(testFile));
            addpath(testCase.BaseDir);
            addpath(fullfile(testCase.BaseDir, 'core'));
            testCase.Config = load_compiler_config(fullfile( ...
                testCase.BaseDir, 'configs', ...
                'compiler_config.example.json'));
        end
    end

    methods (Test)
        function testValidRequestIsProjectedAndResolved(testCase)
            fixture = TestCompilerPipeline.tempFixture();
            request = TestCompilerPipeline.validRequest();
            request.method = 'M2';
            request.c0 = 0.04;
            request.c1 = 0.10;
            request.c2 = 0.16;
            request.w = 4;
            path = fullfile(fixture.dir, 'request.json');
            TestCompilerPipeline.writeJson(path, request);

            parsed = parse_and_validate_request(path, testCase.Config);

            testCase.verifyEqual(parsed.request_id, 'm03-m1-001');
            testCase.verifyEqual(parsed.method, 'M2');
            testCase.verifyEqual(parsed.effective_parameters.c_projected, ...
                0.10, 'AbsTol', 100 * eps);
            testCase.verifyEqual(parsed.output_dir, ...
                fullfile(fixture.dir, 'outputs'));
            testCase.verifyEqual(numel(parsed.raw_request_sha256), 64);
            testCase.verifyEqual(numel(parsed.request_semantic_sha256), 64);
        end

        function testMissingAndExtraFieldsRejected(testCase)
            fixture = TestCompilerPipeline.tempFixture();
            missing = rmfield(TestCompilerPipeline.validRequest(), 'w');
            missingPath = fullfile(fixture.dir, 'missing.json');
            TestCompilerPipeline.writeJson(missingPath, missing);
            testCase.verifyError(@() parse_and_validate_request( ...
                missingPath, testCase.Config), ...
                'MATLABGyroid:InvalidRequest');

            extra = TestCompilerPipeline.validRequest();
            extra.unused = 1;
            extraPath = fullfile(fixture.dir, 'extra.json');
            TestCompilerPipeline.writeJson(extraPath, extra);
            testCase.verifyError(@() parse_and_validate_request( ...
                extraPath, testCase.Config), ...
                'MATLABGyroid:InvalidRequest');
        end

        function testInvalidRequestIdRejected(testCase)
            fixture = TestCompilerPipeline.tempFixture();
            request = TestCompilerPipeline.validRequest();
            request.request_id = '../unsafe';
            path = fullfile(fixture.dir, 'unsafe.json');
            TestCompilerPipeline.writeJson(path, request);

            testCase.verifyError(@() parse_and_validate_request( ...
                path, testCase.Config), ...
                'MATLABGyroid:InvalidRequest');
        end

        function testDisallowedProductionResolutionRejected(testCase)
            fixture = TestCompilerPipeline.tempFixture();
            request = TestCompilerPipeline.validRequest();
            request.resolution = 8;
            path = fullfile(fixture.dir, 'resolution.json');
            TestCompilerPipeline.writeJson(path, request);

            testCase.verifyError(@() parse_and_validate_request( ...
                path, testCase.Config), ...
                'MATLABGyroid:InvalidRequest');
        end

        function testSemanticHashExcludesIdAndOutputPath(testCase)
            firstFixture = TestCompilerPipeline.tempFixture();
            secondFixture = TestCompilerPipeline.tempFixture();
            first = TestCompilerPipeline.validRequest();
            second = first;
            second.request_id = 'different-id';
            second.output_dir = 'different-output';
            firstPath = fullfile(firstFixture.dir, 'first.json');
            secondPath = fullfile(secondFixture.dir, 'second.json');
            TestCompilerPipeline.writeJson(firstPath, first);
            TestCompilerPipeline.writeJson(secondPath, second);

            parsedFirst = parse_and_validate_request( ...
                firstPath, testCase.Config);
            parsedSecond = parse_and_validate_request( ...
                secondPath, testCase.Config);

            testCase.verifyEqual(parsedFirst.request_semantic_sha256, ...
                parsedSecond.request_semantic_sha256);
            testCase.verifyNotEqual(parsedFirst.raw_request_sha256, ...
                parsedSecond.raw_request_sha256);
        end

        function testTextHashUsesUtf8Deterministically(testCase)
            first = sha256_text('M03-连续-CSG');
            second = sha256_text('M03-连续-CSG');
            different = sha256_text('M03-continuous-CSG');
            testCase.verifyEqual(first, second);
            testCase.verifyNotEqual(first, different);
            testCase.verifyEqual(numel(first), 64);
        end

        function testMalformedRequestWritesFailureResponseWithoutArtifacts(testCase)
            fixture = TestCompilerPipeline.tempFixture();
            requestPath = fullfile(fixture.dir, 'malformed.json');
            responsePath = fullfile(fixture.dir, 'response.json');
            TestCompilerPipeline.writeText(requestPath, '{ malformed ');

            response = run_geometry_compiler(requestPath, responsePath);

            testCase.verifyFalse(response.valid);
            testCase.verifyEqual(response.failure_code, 'INVALID_REQUEST');
            testCase.verifyEqual(response.validation_stage, ...
                'M03_GEOMETRY_MESH');
            testCase.verifyEqual(jsondecode(fileread(responsePath)), response);
            testCase.verifyEmpty(dir(fullfile(fixture.dir, '**', '*.stl')));
            testCase.verifyEmpty(dir(fullfile( ...
                fixture.dir, '**', '*.manifest.json')));
        end

        function testJsonDirectoryTargetRejectedWithoutNestedArtifact(testCase)
            fixture = TestCompilerPipeline.tempFixture();
            target = fullfile(fixture.dir, 'target.json');
            mkdir(target);

            testCase.verifyError(@() write_json_atomic( ...
                struct('valid', false), target), ...
                'MATLABGyroid:OutputConflict');

            listing = dir(target);
            testCase.verifyEmpty(listing(~[listing.isdir]));
        end

        function testResponseDirectoryRejectedBeforeCompilation(testCase)
            fixture = TestCompilerPipeline.tempFixture();
            requestPath = fullfile(fixture.dir, 'malformed.json');
            responsePath = fullfile(fixture.dir, 'response.json');
            TestCompilerPipeline.writeText(requestPath, '{ malformed ');
            mkdir(responsePath);

            testCase.verifyError(@() run_geometry_compiler( ...
                requestPath, responsePath), ...
                'MATLABGyroid:OutputConflict');

            listing = dir(responsePath);
            testCase.verifyEmpty(listing(~[listing.isdir]));
        end

        function testMethodFailureWritesResponseWithoutArtifacts(testCase)
            fixture = TestCompilerPipeline.tempFixture();
            request = TestCompilerPipeline.validRequest();
            request.w = 4;
            requestPath = fullfile(fixture.dir, 'invalid-method.json');
            responsePath = fullfile(fixture.dir, 'response.json');
            TestCompilerPipeline.writeJson(requestPath, request);

            response = run_geometry_compiler(requestPath, responsePath);

            testCase.verifyFalse(response.valid);
            testCase.verifyEqual(response.failure_code, 'METHOD_CONSTRAINT');
            testCase.verifyEmpty(dir(fullfile(fixture.dir, '**', '*.stl')));
            testCase.verifyEmpty(dir(fullfile( ...
                fixture.dir, '**', '*.manifest.json')));
        end

        function testProductionM1CompilerIsByteDeterministic(testCase)
            firstFixture = TestCompilerPipeline.tempFixture();
            secondFixture = TestCompilerPipeline.tempFixture();
            firstRequest = TestCompilerPipeline.validRequest();
            secondRequest = firstRequest;
            secondRequest.request_id = 'm03-m1-002';
            firstRequestPath = fullfile(firstFixture.dir, 'request.json');
            secondRequestPath = fullfile(secondFixture.dir, 'request.json');
            firstResponsePath = fullfile(firstFixture.dir, 'response.json');
            secondResponsePath = fullfile(secondFixture.dir, 'response.json');
            TestCompilerPipeline.writeJson(firstRequestPath, firstRequest);
            TestCompilerPipeline.writeJson(secondRequestPath, secondRequest);

            firstResponse = run_geometry_compiler( ...
                firstRequestPath, firstResponsePath);
            secondResponse = run_geometry_compiler( ...
                secondRequestPath, secondResponsePath);

            testCase.assertTrue(firstResponse.valid, ...
                sprintf('first compile failed [%s]: %s', ...
                firstResponse.failure_code, firstResponse.failure_message));
            testCase.assertTrue(secondResponse.valid, ...
                sprintf('second compile failed [%s]: %s', ...
                secondResponse.failure_code, secondResponse.failure_message));
            testCase.verifyEqual(firstResponse.geometry_identity_sha256, ...
                secondResponse.geometry_identity_sha256);
            testCase.verifyEqual(firstResponse.artifacts.stl_sha256, ...
                secondResponse.artifacts.stl_sha256);
            testCase.verifyEqual(firstResponse.mesh_qc.boundary_edge_count, 0);
            testCase.verifyEqual(firstResponse.mesh_qc.nonmanifold_edge_count, 0);
            testCase.verifyEqual(firstResponse.mesh_qc. ...
                self_intersection_pair_count, 0);
            testCase.verifyEqual( ...
                firstResponse.mesh_qc.solid_connectivity, 26);
            testCase.verifyEqual( ...
                firstResponse.mesh_qc.solid_component_count, 1);
            testCase.verifyEqual( ...
                firstResponse.mesh_qc.void_connectivity, 26);
            testCase.verifyGreaterThanOrEqual( ...
                firstResponse.mesh_qc.void_component_count, 1);
            testCase.verifyTrue(isstruct(firstResponse.diagnostics));
            testCase.verifyEqual( ...
                firstResponse.diagnostics.interior_cell_count, ...
                firstResponse.diagnostics.interior_solid_count + ...
                firstResponse.diagnostics.interior_void_count);

            manifest = jsondecode(fileread( ...
                firstResponse.artifacts.manifest_path));
            testCase.verifyEqual( ...
                manifest.discretization.reference_length_mm, 1);
            testCase.verifyEqual( ...
                manifest.discretization.physical_bounds_mm.x(:)', [0, 1]);
            testCase.verifyEqual( ...
                manifest.discretization.physical_bounds_mm.y(:)', [0, 1]);
            testCase.verifyEqual( ...
                manifest.discretization.physical_bounds_mm.z(:)', [0, 2]);
            testCase.verifyEqual( ...
                manifest.discretization.interior_cell_count, ...
                manifest.discretization.interior_solid_count + ...
                manifest.discretization.interior_void_count);
            testCase.verifyEqual( ...
                manifest.discretization.void_connectivity, 26);
            testCase.verifyEqual( ...
                manifest.discretization.void_component_count, ...
                firstResponse.mesh_qc.void_component_count);
            testCase.verifyEqual(firstResponse.descriptors, 'not_computed');
            testCase.verifyEqual(firstResponse.abaqus_gate0, 'not_computed');
        end

        function testProductionM2CompilerPassesM03Gate(testCase)
            fixture = TestCompilerPipeline.tempFixture();
            request = TestCompilerPipeline.validRequest();
            request.request_id = 'm03-m2-production-001';
            request.method = 'M2';
            request.c0 = 0.066666;
            request.c1 = 0.066666;
            request.c2 = 0.066666;
            request.w = 3.54258;
            requestPath = fullfile(fixture.dir, 'request.json');
            responsePath = fullfile(fixture.dir, 'response.json');
            TestCompilerPipeline.writeJson(requestPath, request);

            response = run_geometry_compiler(requestPath, responsePath);

            testCase.assertTrue(response.valid, ...
                sprintf('M2 compile failed [%s]: %s', ...
                response.failure_code, response.failure_message));
            testCase.verifyEqual(response.mesh_qc.component_count, 1);
            testCase.verifyEqual(response.mesh_qc.solid_component_count, 1);
            testCase.verifyEqual( ...
                response.mesh_qc.float32_degenerate_face_count, 0);
            testCase.verifyEqual( ...
                response.mesh_qc.self_intersection_pair_count, 0);
            testCase.verifyTrue(isfile(response.artifacts.stl_path));
            testCase.verifyTrue(isfile(response.artifacts.manifest_path));
        end

        function testProductionM3CompilerPassesM03Gate(testCase)
            fixture = TestCompilerPipeline.tempFixture();
            request = TestCompilerPipeline.validRequest();
            request.request_id = 'm03-m3-production-001';
            request.method = 'M3';
            request.c0 = 0.057717;
            request.c1 = 0.118714;
            request.c2 = 0.188234;
            request.w = 6.71552;
            requestPath = fullfile(fixture.dir, 'request.json');
            responsePath = fullfile(fixture.dir, 'response.json');
            TestCompilerPipeline.writeJson(requestPath, request);

            response = run_geometry_compiler(requestPath, responsePath);

            testCase.assertTrue(response.valid, ...
                sprintf('M3 compile failed [%s]: %s', ...
                response.failure_code, response.failure_message));
            testCase.verifyEqual(response.mesh_qc.component_count, 1);
            testCase.verifyEqual(response.mesh_qc.solid_component_count, 1);
            testCase.verifyEqual( ...
                response.mesh_qc.float32_degenerate_face_count, 0);
            testCase.verifyEqual( ...
                response.mesh_qc.self_intersection_pair_count, 0);
            testCase.verifyTrue(isfile(response.artifacts.stl_path));
            testCase.verifyTrue(isfile(response.artifacts.manifest_path));
        end
    end

    methods (Static, Access = private)
        function fixture = tempFixture()
            fixture.dir = tempname;
            mkdir(fixture.dir);
            fixture.cleanup = onCleanup(@() rmdir(fixture.dir, 's'));
        end

        function request = validRequest()
            request = struct('schema_version', '1.0', ...
                'request_id', 'm03-m1-001', 'method', 'M1', ...
                'c0', 0.0700794, 'c1', 0.1246504, ...
                'c2', 0.0693255, 'w', 0, ...
                'resolution', 96, 'output_dir', 'outputs');
        end

        function writeJson(path, value)
            fileId = fopen(path, 'w');
            assert(fileId ~= -1);
            cleanup = onCleanup(@() fclose(fileId));
            fprintf(fileId, '%s', jsonencode(value));
        end

        function writeText(path, value)
            fileId = fopen(path, 'w');
            assert(fileId ~= -1);
            cleanup = onCleanup(@() fclose(fileId));
            fprintf(fileId, '%s', value);
        end
    end
end
