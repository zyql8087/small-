classdef TestDescriptorCompiler < matlab.unittest.TestCase
%TESTDESCRIPTORCOMPILER Tests authenticated dual-profile M04 publication.

    properties (Access = private)
        BaseDir
        FixtureDir
        RequestPath
        M03ResponsePath
        M04ResponsePath
    end

    methods (TestClassSetup)
        function setupClass(testCase)
            testCase.BaseDir = fileparts(fileparts(mfilename('fullpath')));
            addpath(testCase.BaseDir);
            addpath(fullfile(testCase.BaseDir, 'core'));
        end
    end

    methods (TestMethodSetup)
        function createAuthenticatedM03Fixture(testCase)
            testCase.FixtureDir = tempname;
            mkdir(testCase.FixtureDir);
            testCase.RequestPath = fullfile(testCase.FixtureDir, 'request.json');
            testCase.M03ResponsePath = fullfile(testCase.FixtureDir, 'm03.json');
            testCase.M04ResponsePath = fullfile(testCase.FixtureDir, 'm04.json');
            request = TestDescriptorCompiler.validRequest();
            request.output_dir = 'outputs';
            TestDescriptorCompiler.overwriteJson(testCase.RequestPath, request);

            m03 = run_geometry_compiler(testCase.RequestPath, ...
                testCase.M03ResponsePath);
            testCase.assertTrue(m03.valid, sprintf( ...
                'M03 fixture failed [%s]: %s', ...
                m03.failure_code, m03.failure_message));
        end
    end

    methods (TestMethodTeardown)
        function removeFixture(testCase)
            if ~isempty(testCase.FixtureDir) && ...
                    exist(testCase.FixtureDir, 'dir') == 7
                rmdir(testCase.FixtureDir, 's');
            end
        end
    end

    methods (Test)
        function testPublishesNamedDescriptorProfiles(testCase)
            response = run_descriptor_compiler(testCase.RequestPath, ...
                testCase.M03ResponsePath, testCase.M04ResponsePath);

            testCase.verifyTrue(response.valid);
            testCase.verifyEqual(string(fieldnames(response.descriptors))', ...
                ["legacy_small", "physical_m04"]);
            testCase.verifyFalse(isfield(response, 'relativeVolume'));
            testCase.verifyTrue(isfile(response.artifacts.manifest_path));
            testCase.verifyEqual(response.validation_stage, ...
                'M04_DUAL_DESCRIPTORS');
            testCase.verifyFalse(response.abaqus_gate0.solver_ready);
        end

        function testCanonicalDescriptorHashIsOutputPathIndependent(testCase)
            first = run_descriptor_compiler(testCase.RequestPath, ...
                testCase.M03ResponsePath, testCase.M04ResponsePath);
            secondPath = fullfile(testCase.FixtureDir, 'm04-second.json');
            second = run_descriptor_compiler(testCase.RequestPath, ...
                testCase.M03ResponsePath, secondPath);

            testCase.verifyTrue(first.valid);
            testCase.verifyTrue(second.valid);
            testCase.verifyEqual(first.descriptor_canonical_sha256, ...
                second.descriptor_canonical_sha256);
        end

        function testRejectsMutatedRequestAndPreservesM03(testCase)
            request = jsondecode(fileread(testCase.RequestPath));
            request.c0 = request.c0 + 0.001;
            TestDescriptorCompiler.overwriteJson(testCase.RequestPath, request);

            testCase.verifyM04FailurePreservesM03();
        end

        function testRejectsMutatedM03ResponseAndPreservesM03(testCase)
            m03 = testCase.readM03Response();
            m03.geometry_identity_sha256 = repmat('0', 1, 64);
            TestDescriptorCompiler.overwriteJson(testCase.M03ResponsePath, m03);

            testCase.verifyM04FailurePreservesM03();
        end

        function testRejectsMutatedManifestAndPreservesM03(testCase)
            m03 = testCase.readM03Response();
            manifest = jsondecode(fileread(m03.artifacts.manifest_path));
            manifest.discretization.units = 'm';
            TestDescriptorCompiler.overwriteJson( ...
                m03.artifacts.manifest_path, manifest);
            m03.artifacts.manifest_sha256 = sha256_file( ...
                m03.artifacts.manifest_path, ...
                'MATLABGyroid:TestFailure', 'mutated manifest');
            TestDescriptorCompiler.overwriteJson(testCase.M03ResponsePath, m03);

            testCase.verifyM04FailurePreservesM03();
        end

        function testRejectsMutatedStlAndPreservesM03(testCase)
            m03 = testCase.readM03Response();
            fileId = fopen(m03.artifacts.stl_path, 'r+b');
            testCase.assertNotEqual(fileId, -1);
            cleanup = onCleanup(@() fclose(fileId));
            fseek(fileId, -1, 'eof');
            fwrite(fileId, uint8(1), 'uint8');
            clear cleanup;

            testCase.verifyM04FailurePreservesM03();
        end

        function testRejectsManifestBoundsResolutionAndVersionMismatches(testCase)
            mismatchMutators = { ...
                @(manifest) setfield(manifest, 'compiler_version', ...
                'matlab-gyroid-999.0.0'), ... %#ok<SFLD>
                @(manifest) TestDescriptorCompiler.setResolution(manifest, 128), ...
                @(manifest) TestDescriptorCompiler.setXBounds(manifest, [0, 2])};
            for index = 1:numel(mismatchMutators)
                testCase.resetM03Fixture();
                m03 = testCase.readM03Response();
                manifest = jsondecode(fileread(m03.artifacts.manifest_path));
                manifest = mismatchMutators{index}(manifest);
                TestDescriptorCompiler.overwriteJson( ...
                    m03.artifacts.manifest_path, manifest);
                m03.artifacts.manifest_sha256 = sha256_file( ...
                    m03.artifacts.manifest_path, ...
                    'MATLABGyroid:TestFailure', 'mutated manifest');
                TestDescriptorCompiler.overwriteJson(testCase.M03ResponsePath, m03);
                testCase.verifyM04FailurePreservesM03();
            end
        end

        function testRejectsExistingM04ResponseFile(testCase)
            TestDescriptorCompiler.overwriteJson(testCase.M04ResponsePath, ...
                struct('unrelated', true));

            testCase.verifyError(@() run_descriptor_compiler( ...
                testCase.RequestPath, testCase.M03ResponsePath, ...
                testCase.M04ResponsePath), 'MATLABGyroid:OutputConflict');
        end

        function testRejectsM04ResponseDirectory(testCase)
            mkdir(testCase.M04ResponsePath);

            testCase.verifyError(@() run_descriptor_compiler( ...
                testCase.RequestPath, testCase.M03ResponsePath, ...
                testCase.M04ResponsePath), 'MATLABGyroid:OutputConflict');
        end
    end

    methods (Access = private)
        function m03 = readM03Response(testCase)
            m03 = jsondecode(fileread(testCase.M03ResponsePath));
        end

        function resetM03Fixture(testCase)
            if exist(testCase.FixtureDir, 'dir') == 7
                rmdir(testCase.FixtureDir, 's');
            end
            testCase.createAuthenticatedM03Fixture();
        end

        function verifyM04FailurePreservesM03(testCase)
            m03 = testCase.readM03Response();
            before = struct('response', sha256_file(testCase.M03ResponsePath, ...
                'MATLABGyroid:TestFailure', 'M03 response'), ...
                'manifest', sha256_file(m03.artifacts.manifest_path, ...
                'MATLABGyroid:TestFailure', 'M03 manifest'), ...
                'stl', sha256_file(m03.artifacts.stl_path, ...
                'MATLABGyroid:TestFailure', 'M03 STL'));

            response = run_descriptor_compiler(testCase.RequestPath, ...
                testCase.M03ResponsePath, testCase.M04ResponsePath);

            testCase.verifyFalse(response.valid);
            testCase.verifyEqual(response.failure_code, 'M03_ARTIFACT_MISMATCH');
            testCase.verifyEqual(sha256_file(testCase.M03ResponsePath, ...
                'MATLABGyroid:TestFailure', 'M03 response'), before.response);
            testCase.verifyEqual(sha256_file(m03.artifacts.manifest_path, ...
                'MATLABGyroid:TestFailure', 'M03 manifest'), before.manifest);
            testCase.verifyEqual(sha256_file(m03.artifacts.stl_path, ...
                'MATLABGyroid:TestFailure', 'M03 STL'), before.stl);
        end
    end

    methods (Static, Access = private)
        function request = validRequest()
            request = struct('schema_version', '1.0', ...
                'request_id', 'm04-m1-001', 'method', 'M1', ...
                'c0', 0.0700794, 'c1', 0.1246504, ...
                'c2', 0.0693255, 'w', 0, 'resolution', 96, ...
                'output_dir', 'outputs');
        end

        function overwriteJson(path, value)
            fileId = fopen(path, 'w', 'n', 'UTF-8');
            assert(fileId ~= -1);
            cleanup = onCleanup(@() fclose(fileId));
            fprintf(fileId, '%s', jsonencode(value));
        end

        function manifest = setResolution(manifest, value)
            manifest.discretization.resolution = value;
        end

        function manifest = setXBounds(manifest, value)
            manifest.discretization.physical_bounds_mm.x = value;
        end
    end
end
