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
                'c0', 0.10, 'c1', 0.10, 'c2', 0.10, 'w', 0, ...
                'resolution', 96, 'output_dir', 'outputs');
        end

        function writeJson(path, value)
            fileId = fopen(path, 'w');
            assert(fileId ~= -1);
            cleanup = onCleanup(@() fclose(fileId));
            fprintf(fileId, '%s', jsonencode(value));
        end
    end
end
