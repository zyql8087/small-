classdef TestBootstrap < matlab.unittest.TestCase
%TESTBOOTSTRAP Unit tests for MATLAB geometry compiler bootstrap phase
%   This test class validates the core contract implementation for the
%   graded Gyroid geometry compiler built on MATLAB R2023b.
%
%   Tests cover:
%   - Compiler version string validation
%   - Descriptor ordering enforcement (error, not warning)
%   - Configuration path resolution (relative to config file)
%   - solid_convention = sheet_band enforcement
%   - Malformed JSON rejection
%   - Missing field rejection
%   - Wrong schema_version rejection
%   - Wrong descriptor order rejection
%   - Invalid resolution type rejection (string instead of numeric)
%   - Invalid reference_length_mm type rejection
%   - Invalid method_bounds type rejection (scalar instead of struct)
%   - Invalid mesh_qc type rejection (scalar instead of struct)
%   - Missing method (M1/M2/M3) rejection
%   - Invalid bounds structure rejection
%   - lower > upper rejection
%   - Wrong solid_convention rejection
%   - Descriptor definition order mismatch rejection
%   - Descriptor definition schema mismatch rejection
%   - All errors use identifier MATLABGyroid:InvalidConfig
%   - Image Processing Toolbox availability (bwdist, bwconncomp, bwskel)

    properties (Constant, Access = protected)
        ERROR_ID = 'MATLABGyroid:InvalidConfig'
    end

    properties (Access = private)
        BaseDir
    end

    methods (TestClassSetup)
        function setupClass(testCase)
            % Derive project root from this file's location
            thisFile = mfilename('fullpath');
            testCase.BaseDir = fileparts(strrep(thisFile, '\', '/'));
            % BaseDir is .../geometry_compiler_matlab/tests, go up one level
            testCase.BaseDir = fileparts(testCase.BaseDir);
            % Add core and configs to path
            addpath(fullfile(testCase.BaseDir, 'core'));
            addpath(fullfile(testCase.BaseDir, 'configs'));
        end
    end

    methods(Test)

        %% ===== Positive tests =====

        function testCompilerVersion(testCase)
            % Verify exact version identifier
            expectedVersion = 'matlab-gyroid-0.1.0';
            actualVersion = compiler_version();
            testCase.assertEqual(actualVersion, expectedVersion);
        end

        function testDescriptorOrdering(testCase)
            % Verify fixed descriptor contract order from config
            configPath = fullfile(testCase.BaseDir, 'configs', 'compiler_config.example.json');
            testCase.assertTrue(exist(configPath, 'file') == 2, 'Example config not found');

            config = load_compiler_config(configPath);

            expectedOrder = {'relativeVolume', 'relativeArea', 'thickness', ...
                            'poreDiameter', 'areaMean'};

            testCase.assertEqual(length(config.descriptor_names), length(expectedOrder));

            for i = 1:length(expectedOrder)
                testCase.assertEqual(string(config.descriptor_names{i}), string(expectedOrder{i}));
            end
        end

        function testConfigPathResolution(testCase)
            % Verify descriptor_definition_path is resolved relative to config
            configPath = fullfile(testCase.BaseDir, 'configs', 'compiler_config.example.json');
            testCase.assertTrue(exist(configPath, 'file') == 2, 'Example config not found');

            config = load_compiler_config(configPath);

            testCase.assertFalse(isempty(config.descriptor_definition_path));
            testCase.assertTrue(exist(config.descriptor_definition_path, 'file') ~= 0, ...
                'Descriptor file not found at resolved path');
        end

        function testSolidConvention(testCase)
            % Verify solid_convention is sheet_band
            configPath = fullfile(testCase.BaseDir, 'configs', 'compiler_config.example.json');
            config = load_compiler_config(configPath);

            testCase.assertEqual(config.solid_convention, 'sheet_band');
        end

        function testSchemaVersionEnforced(testCase)
            % Verify schema_version must be "1.0"
            configPath = fullfile(testCase.BaseDir, 'configs', 'compiler_config.example.json');
            config = load_compiler_config(configPath);

            testCase.assertEqual(config.schema_version, '1.0');
        end

        function testMethodBoundsNamedVariables(testCase)
            % Verify method_bounds uses named variables with proper structure
            configPath = fullfile(testCase.BaseDir, 'configs', 'compiler_config.example.json');
            config = load_compiler_config(configPath);

            % M1: c0, c1, c2 active; w fixed at 0
            m1 = config.method_bounds.M1;
            testCase.assertTrue(isfield(m1, 'active_variables'));
            testCase.assertTrue(isfield(m1, 'fixed_variables'));
            testCase.assertTrue(isfield(m1.bounds, 'c0'));
            testCase.assertTrue(isfield(m1.bounds, 'c1'));
            testCase.assertTrue(isfield(m1.bounds, 'c2'));
            testCase.assertEqual(m1.fixed_variables.w, 0);

            % M2: c_projected and w active; projection defined
            m2 = config.method_bounds.M2;
            testCase.assertTrue(isfield(m2, 'projection'));
            testCase.assertTrue(isfield(m2.bounds, 'c_projected'));
            testCase.assertTrue(isfield(m2.bounds, 'w'));

            % M3: all four active
            m3 = config.method_bounds.M3;
            testCase.assertTrue(isfield(m3.bounds, 'c0'));
            testCase.assertTrue(isfield(m3.bounds, 'c1'));
            testCase.assertTrue(isfield(m3.bounds, 'c2'));
            testCase.assertTrue(isfield(m3.bounds, 'w'));
        end

        function testImageProcessingToolbox(testCase)
            % Verify bwdist, bwconncomp, bwskel are available
            hasIPT = false;
            try
                dummy_img = false(10, 10, 10);
                distance_map = bwdist(dummy_img);
                hasIPT = true;
            catch
                hasIPT = false;
            end

            testCase.verifyTrue(hasIPT, 'Image Processing Toolbox is mandatory');

            essential_funcs = {'bwdist', 'bwconncomp', 'bwskel'};
            for i = 1:length(essential_funcs)
                funcExists = exist(essential_funcs{i}, 'file');
                testCase.assertTrue(funcExists ~= 0, ...
                    sprintf('Function "%s" must be available', essential_funcs{i}));
            end
        end

        %% ===== Negative tests: JSON and field presence =====

        function testInvalidJsonRejected(testCase)
            % Verify malformed JSON throws MATLABGyroid:InvalidConfig
            tempFile = [tempname '.json'];
            cleanupObj = onCleanup(@() TestBootstrap.deleteFile(tempFile));

            fid = fopen(tempFile, 'w');
            fprintf(fid, '{ this is not valid json }}}');
            fclose(fid);

            try
                load_compiler_config(tempFile);
                testCase.fail('Expected error for invalid JSON');
            catch ME
                testCase.assertEqual(ME.identifier, testCase.ERROR_ID);
            end
        end

        function testMissingFieldRejected(testCase)
            % Verify missing required field throws MATLABGyroid:InvalidConfig
            tempFile = [tempname '.json'];
            cleanupObj = onCleanup(@() TestBootstrap.deleteFile(tempFile));

            fid = fopen(tempFile, 'w');
            fprintf(fid, '{"schema_version": "1.0"}');
            fclose(fid);

            try
                load_compiler_config(tempFile);
                testCase.fail('Expected error for missing field');
            catch ME
                testCase.assertEqual(ME.identifier, testCase.ERROR_ID);
                testCase.verifyTrue(contains(ME.message, 'Missing required'));
            end
        end

        function testWrongSchemaVersionRejected(testCase)
            % Verify wrong schema_version throws MATLABGyroid:InvalidConfig
            tempFile = [tempname '.json'];
            cleanupObj = onCleanup(@() TestBootstrap.deleteFile(tempFile));

            data = TestBootstrap.loadExampleConfig(testCase.BaseDir);
            data.schema_version = '2.0';
            TestBootstrap.writeJson(tempFile, data);

            try
                load_compiler_config(tempFile);
                testCase.fail('Expected error for wrong schema_version');
            catch ME
                testCase.assertEqual(ME.identifier, testCase.ERROR_ID);
                testCase.verifyTrue(contains(ME.message, 'schema_version'));
            end
        end

        function testWrongDescriptorOrderRejected(testCase)
            % Verify wrong descriptor order throws MATLABGyroid:InvalidConfig
            tempDir = tempname;
            mkdir(tempDir);
            cleanupDir = onCleanup(@() TestBootstrap.deleteDir(tempDir));

            % Copy descriptor definition into temp dir (relative path)
            srcDesc = fullfile(testCase.BaseDir, 'configs', 'descriptor_definition.json');
            copyfile(srcDesc, fullfile(tempDir, 'descriptor_definition.json'));

            data = TestBootstrap.loadExampleConfig(testCase.BaseDir);
            data.descriptor_names = {"areaMean", "relativeVolume", "relativeArea", "thickness", "poreDiameter"};
            data.descriptor_definition_path = 'descriptor_definition.json';
            tempFile = fullfile(tempDir, 'bad_order.json');
            TestBootstrap.writeJson(tempFile, data);

            try
                load_compiler_config(tempFile);
                testCase.fail('Expected error for wrong descriptor order');
            catch ME
                testCase.assertEqual(ME.identifier, testCase.ERROR_ID);
                testCase.verifyTrue(contains(ME.message, 'Descriptor order'));
            end
        end

        %% ===== Negative tests: type validation =====

        function testInvalidResolutionTypeRejected(testCase)
            % Verify resolution="x" (string) is rejected
            tempFile = [tempname '.json'];
            cleanupObj = onCleanup(@() TestBootstrap.deleteFile(tempFile));

            data = TestBootstrap.loadExampleConfig(testCase.BaseDir);
            data.resolution = 'x';
            TestBootstrap.writeJson(tempFile, data);

            try
                load_compiler_config(tempFile);
                testCase.fail('Expected error for string resolution');
            catch ME
                testCase.assertEqual(ME.identifier, testCase.ERROR_ID);
                testCase.verifyTrue(contains(ME.message, 'Resolution'));
            end
        end

        function testInvalidRefLengthTypeRejected(testCase)
            % Verify reference_length_mm="x" (string) is rejected
            tempFile = [tempname '.json'];
            cleanupObj = onCleanup(@() TestBootstrap.deleteFile(tempFile));

            data = TestBootstrap.loadExampleConfig(testCase.BaseDir);
            data.reference_length_mm = 'x';
            TestBootstrap.writeJson(tempFile, data);

            try
                load_compiler_config(tempFile);
                testCase.fail('Expected error for string reference_length_mm');
            catch ME
                testCase.assertEqual(ME.identifier, testCase.ERROR_ID);
                testCase.verifyTrue(contains(ME.message, 'reference_length_mm'));
            end
        end

        function testInvalidMethodBoundsTypeRejected(testCase)
            % Verify method_bounds=1 (scalar) is rejected
            tempFile = [tempname '.json'];
            cleanupObj = onCleanup(@() TestBootstrap.deleteFile(tempFile));

            data = TestBootstrap.loadExampleConfig(testCase.BaseDir);
            data.method_bounds = 1;
            TestBootstrap.writeJson(tempFile, data);

            try
                load_compiler_config(tempFile);
                testCase.fail('Expected error for scalar method_bounds');
            catch ME
                testCase.assertEqual(ME.identifier, testCase.ERROR_ID);
                testCase.verifyTrue(contains(ME.message, 'method_bounds'));
            end
        end

        function testInvalidMeshQcTypeRejected(testCase)
            % Verify mesh_qc=1 (scalar) is rejected
            tempFile = [tempname '.json'];
            cleanupObj = onCleanup(@() TestBootstrap.deleteFile(tempFile));

            data = TestBootstrap.loadExampleConfig(testCase.BaseDir);
            data.mesh_qc = 1;
            TestBootstrap.writeJson(tempFile, data);

            try
                load_compiler_config(tempFile);
                testCase.fail('Expected error for scalar mesh_qc');
            catch ME
                testCase.assertEqual(ME.identifier, testCase.ERROR_ID);
                testCase.verifyTrue(contains(ME.message, 'mesh_qc'));
            end
        end

        %% ===== Negative tests: method_bounds structure =====

        function testMissingMethodRejected(testCase)
            % Verify method_bounds without M2 is rejected
            tempFile = [tempname '.json'];
            cleanupObj = onCleanup(@() TestBootstrap.deleteFile(tempFile));

            data = TestBootstrap.loadExampleConfig(testCase.BaseDir);
            data.method_bounds = rmfield(data.method_bounds, 'M2');
            TestBootstrap.writeJson(tempFile, data);

            try
                load_compiler_config(tempFile);
                testCase.fail('Expected error for missing M2');
            catch ME
                testCase.assertEqual(ME.identifier, testCase.ERROR_ID);
                testCase.verifyTrue(contains(ME.message, 'M2'));
            end
        end

        function testInvalidBoundsNestedStructureRejected(testCase)
            % Verify bounds with wrong nested structure is rejected
            tempFile = [tempname '.json'];
            cleanupObj = onCleanup(@() TestBootstrap.deleteFile(tempFile));

            data = TestBootstrap.loadExampleConfig(testCase.BaseDir);
            % Replace M1.bounds.c0 with a scalar instead of struct
            data.method_bounds.M1.bounds.c0 = 0.5;
            TestBootstrap.writeJson(tempFile, data);

            try
                load_compiler_config(tempFile);
                testCase.fail('Expected error for invalid bounds structure');
            catch ME
                testCase.assertEqual(ME.identifier, testCase.ERROR_ID);
                testCase.verifyTrue(contains(ME.message, 'bounds'));
            end
        end

        function testLowerGreaterThanUpperRejected(testCase)
            % Verify lower > upper is rejected
            tempFile = [tempname '.json'];
            cleanupObj = onCleanup(@() TestBootstrap.deleteFile(tempFile));

            data = TestBootstrap.loadExampleConfig(testCase.BaseDir);
            data.method_bounds.M1.bounds.c0.lower = 0.95;
            data.method_bounds.M1.bounds.c0.upper = 0.10;
            TestBootstrap.writeJson(tempFile, data);

            try
                load_compiler_config(tempFile);
                testCase.fail('Expected error for lower > upper');
            catch ME
                testCase.assertEqual(ME.identifier, testCase.ERROR_ID);
                testCase.verifyTrue(contains(ME.message, 'lower'));
            end
        end

        %% ===== Negative tests: solid_convention =====

        function testWrongSolidConventionRejected(testCase)
            % Verify wrong solid_convention is rejected
            tempFile = [tempname '.json'];
            cleanupObj = onCleanup(@() TestBootstrap.deleteFile(tempFile));

            data = TestBootstrap.loadExampleConfig(testCase.BaseDir);
            data.solid_convention = 'signed_level_set';
            TestBootstrap.writeJson(tempFile, data);

            try
                load_compiler_config(tempFile);
                testCase.fail('Expected error for wrong solid_convention');
            catch ME
                testCase.assertEqual(ME.identifier, testCase.ERROR_ID);
                testCase.verifyTrue(contains(ME.message, 'solid_convention'));
            end
        end

        %% ===== Negative tests: descriptor definition consistency =====

        function testDescriptorDefinitionOrderMismatchRejected(testCase)
            % Verify descriptor definition with wrong order is rejected
            tempDir = tempname;
            mkdir(tempDir);
            cleanupDir = onCleanup(@() TestBootstrap.deleteDir(tempDir));

            % Create a minimal descriptor definition with wrong order
            % (relativeArea before relativeVolume)
            badDescJson = ['{"schema_version":"1.0","descriptors":[' ...
                '{"name":"relativeArea","formula":"x","units":"mm","computation_method":"x"},' ...
                '{"name":"relativeVolume","formula":"x","units":"mm","computation_method":"x"},' ...
                '{"name":"thickness","formula":"x","units":"mm","computation_method":"x"},' ...
                '{"name":"poreDiameter","formula":"x","units":"mm","computation_method":"x"},' ...
                '{"name":"areaMean","formula":"x","units":"mm","computation_method":"x"}' ...
                ']}'];
            badDescPath = fullfile(tempDir, 'descriptor_definition.json');
            fid = fopen(badDescPath, 'w');
            fprintf(fid, '%s', badDescJson);
            fclose(fid);

            % Config with correct order but pointing to bad descriptor definition
            data = TestBootstrap.loadExampleConfig(testCase.BaseDir);
            data.descriptor_definition_path = 'descriptor_definition.json';
            tempFile = fullfile(tempDir, 'config.json');
            TestBootstrap.writeJson(tempFile, data);

            try
                load_compiler_config(tempFile);
                testCase.fail('Expected error for descriptor definition order mismatch');
            catch ME
                testCase.assertEqual(ME.identifier, testCase.ERROR_ID);
                testCase.verifyTrue(contains(ME.message, 'order'));
            end
        end

        function testDescriptorDefinitionSchemaMismatchRejected(testCase)
            % Verify descriptor definition with wrong schema_version is rejected
            tempDir = tempname;
            mkdir(tempDir);
            cleanupDir = onCleanup(@() TestBootstrap.deleteDir(tempDir));

            % Create a descriptor definition with wrong schema_version
            % using string replacement to avoid jsonencode roundtrip issues
            srcDesc = fullfile(testCase.BaseDir, 'configs', 'descriptor_definition.json');
            raw = fileread(srcDesc);
            raw = strrep(raw, '"schema_version": "1.0"', '"schema_version": "2.0"');
            badDescPath = fullfile(tempDir, 'descriptor_definition.json');
            fid = fopen(badDescPath, 'w');
            fprintf(fid, '%s', raw);
            fclose(fid);

            data = TestBootstrap.loadExampleConfig(testCase.BaseDir);
            data.descriptor_definition_path = 'descriptor_definition.json';
            tempFile = fullfile(tempDir, 'config.json');
            TestBootstrap.writeJson(tempFile, data);

            try
                load_compiler_config(tempFile);
                testCase.fail('Expected error for descriptor definition schema mismatch');
            catch ME
                testCase.assertEqual(ME.identifier, testCase.ERROR_ID);
                testCase.verifyTrue(contains(ME.message, 'schema_version'));
            end
        end

        %% ===== v4 positive tests: boundary values and geometry_parameters =====

        function testBoundaryValuesMatchSmallData(testCase)
            % Verify parameter bounds match Small archived valid records
            configPath = fullfile(testCase.BaseDir, 'configs', 'compiler_config.example.json');
            config = load_compiler_config(configPath);

            % M1: c0, c1, c2 in [0.03, 0.20]
            m1 = config.method_bounds.M1;
            testCase.assertEqual(m1.bounds.c0.lower, 0.03);
            testCase.assertEqual(m1.bounds.c0.upper, 0.20);
            testCase.assertEqual(m1.bounds.c1.lower, 0.03);
            testCase.assertEqual(m1.bounds.c1.upper, 0.20);
            testCase.assertEqual(m1.bounds.c2.lower, 0.03);
            testCase.assertEqual(m1.bounds.c2.upper, 0.20);

            % M2: c_projected in [0.03, 0.20], w in [0.0, 2.5]
            m2 = config.method_bounds.M2;
            testCase.assertEqual(m2.bounds.c_projected.lower, 0.03);
            testCase.assertEqual(m2.bounds.c_projected.upper, 0.20);
            testCase.assertEqual(m2.bounds.w.lower, 0.0);
            testCase.assertEqual(m2.bounds.w.upper, 2.5);

            % M3: c0,c1,c2 in [0.03, 0.20], w in [0.0, 2.5]
            m3 = config.method_bounds.M3;
            testCase.assertEqual(m3.bounds.c0.lower, 0.03);
            testCase.assertEqual(m3.bounds.c0.upper, 0.20);
            testCase.assertEqual(m3.bounds.w.lower, 0.0);
            testCase.assertEqual(m3.bounds.w.upper, 2.5);
        end

        function testM1LevelsInclude160(testCase)
            % Verify M1 levels include at least [96, 128, 160]
            configPath = fullfile(testCase.BaseDir, 'configs', 'compiler_config.example.json');
            config = load_compiler_config(configPath);
            m1Levels = config.method_bounds.M1.levels;
            testCase.assertTrue(all(ismember([96, 128, 160], m1Levels)), ...
                'M1 levels must include 96, 128, 160');
        end

        function testGeometryParametersReturned(testCase)
            % Verify geometry_parameters is loaded and returned correctly
            configPath = fullfile(testCase.BaseDir, 'configs', 'compiler_config.example.json');
            config = load_compiler_config(configPath);

            testCase.assertTrue(isfield(config, 'geometry_parameters'));
            gp = config.geometry_parameters;
            testCase.assertEqual(gp.Lx, 1.0);
            testCase.assertEqual(gp.Ly, 1.0);
            testCase.assertEqual(gp.Lz0, 1.5);
            testCase.assertEqual(char(string(gp.units)), 'mm');
        end

        %% ===== v4 negative tests: geometry_parameters =====

        function testMissingGeometryParametersRejected(testCase)
            % Verify missing geometry_parameters is rejected
            tempFile = [tempname '.json'];
            cleanupObj = onCleanup(@() TestBootstrap.deleteFile(tempFile));

            data = TestBootstrap.loadExampleConfig(testCase.BaseDir);
            data = rmfield(data, 'geometry_parameters');
            TestBootstrap.writeJson(tempFile, data);

            try
                load_compiler_config(tempFile);
                testCase.fail('Expected error for missing geometry_parameters');
            catch ME
                testCase.assertEqual(ME.identifier, testCase.ERROR_ID);
                testCase.verifyTrue(contains(ME.message, 'geometry_parameters'));
            end
        end

        function testInvalidGeometryParametersTypeRejected(testCase)
            % Verify geometry_parameters as string is rejected
            tempFile = [tempname '.json'];
            cleanupObj = onCleanup(@() TestBootstrap.deleteFile(tempFile));

            data = TestBootstrap.loadExampleConfig(testCase.BaseDir);
            data.geometry_parameters = 'bad';
            TestBootstrap.writeJson(tempFile, data);

            try
                load_compiler_config(tempFile);
                testCase.fail('Expected error for non-struct geometry_parameters');
            catch ME
                testCase.assertEqual(ME.identifier, testCase.ERROR_ID);
                testCase.verifyTrue(contains(ME.message, 'geometry_parameters'));
            end
        end

        %% ===== v4 negative tests: active_variables / fixed_variables / projection =====

        function testIllegalActiveVariableRejected(testCase)
            % Verify active_variables=["banana"] is rejected
            tempFile = [tempname '.json'];
            cleanupObj = onCleanup(@() TestBootstrap.deleteFile(tempFile));

            data = TestBootstrap.loadExampleConfig(testCase.BaseDir);
            data.method_bounds.M1.active_variables = {"banana"};
            TestBootstrap.writeJson(tempFile, data);

            try
                load_compiler_config(tempFile);
                testCase.fail('Expected error for illegal active variable');
            catch ME
                testCase.assertEqual(ME.identifier, testCase.ERROR_ID);
                testCase.verifyTrue(contains(ME.message, 'illegal variable'));
            end
        end

        function testMissingFixedVariablesRejected(testCase)
            % Verify removing fixed_variables from M1 is rejected
            tempFile = [tempname '.json'];
            cleanupObj = onCleanup(@() TestBootstrap.deleteFile(tempFile));

            data = TestBootstrap.loadExampleConfig(testCase.BaseDir);
            data.method_bounds.M1 = rmfield(data.method_bounds.M1, 'fixed_variables');
            TestBootstrap.writeJson(tempFile, data);

            try
                load_compiler_config(tempFile);
                testCase.fail('Expected error for missing fixed_variables');
            catch ME
                testCase.assertEqual(ME.identifier, testCase.ERROR_ID);
                testCase.verifyTrue(contains(ME.message, 'fixed_variables'));
            end
        end

        function testMissingProjectionInM2Rejected(testCase)
            % Verify removing projection from M2 is rejected
            tempFile = [tempname '.json'];
            cleanupObj = onCleanup(@() TestBootstrap.deleteFile(tempFile));

            data = TestBootstrap.loadExampleConfig(testCase.BaseDir);
            data.method_bounds.M2 = rmfield(data.method_bounds.M2, 'projection');
            TestBootstrap.writeJson(tempFile, data);

            try
                load_compiler_config(tempFile);
                testCase.fail('Expected error for missing projection in M2');
            catch ME
                testCase.assertEqual(ME.identifier, testCase.ERROR_ID);
            end
        end

        %% ===== v4 negative tests: levels validation =====

        function testEmptyLevelsRejected(testCase)
            % Verify empty levels array is rejected
            tempFile = [tempname '.json'];
            cleanupObj = onCleanup(@() TestBootstrap.deleteFile(tempFile));

            data = TestBootstrap.loadExampleConfig(testCase.BaseDir);
            data.method_bounds.M1.levels = [];
            TestBootstrap.writeJson(tempFile, data);

            try
                load_compiler_config(tempFile);
                testCase.fail('Expected error for empty levels');
            catch ME
                testCase.assertEqual(ME.identifier, testCase.ERROR_ID);
                testCase.verifyTrue(contains(ME.message, 'levels'));
            end
        end

        function testNonIncreasingLevelsRejected(testCase)
            % Verify non-strictly-increasing levels [128, 96, 160] is rejected
            tempFile = [tempname '.json'];
            cleanupObj = onCleanup(@() TestBootstrap.deleteFile(tempFile));

            data = TestBootstrap.loadExampleConfig(testCase.BaseDir);
            data.method_bounds.M1.levels = [128, 96, 160];
            TestBootstrap.writeJson(tempFile, data);

            try
                load_compiler_config(tempFile);
                testCase.fail('Expected error for non-increasing levels');
            catch ME
                testCase.assertEqual(ME.identifier, testCase.ERROR_ID);
                testCase.verifyTrue(contains(ME.message, 'levels'));
            end
        end

        function testNonIntegerLevelsRejected(testCase)
            % Verify non-integer levels [96, 128.5, 160] is rejected
            tempFile = [tempname '.json'];
            cleanupObj = onCleanup(@() TestBootstrap.deleteFile(tempFile));

            data = TestBootstrap.loadExampleConfig(testCase.BaseDir);
            data.method_bounds.M1.levels = [96, 128.5, 160];
            TestBootstrap.writeJson(tempFile, data);

            try
                load_compiler_config(tempFile);
                testCase.fail('Expected error for non-integer levels');
            catch ME
                testCase.assertEqual(ME.identifier, testCase.ERROR_ID);
                testCase.verifyTrue(contains(ME.message, 'levels'));
            end
        end

        function testNonFiniteLevelsRejected(testCase)
            % Verify levels containing Infinity is rejected
            tempDir = tempname;
            mkdir(tempDir);
            cleanupDir = onCleanup(@() TestBootstrap.deleteDir(tempDir));

            srcDesc = fullfile(testCase.BaseDir, 'configs', 'descriptor_definition.json');
            copyfile(srcDesc, fullfile(tempDir, 'descriptor_definition.json'));

            srcCfg = fullfile(testCase.BaseDir, 'configs', 'compiler_config.example.json');
            rawCfg = fileread(srcCfg);
            rawCfg = strrep(rawCfg, '"levels": [96, 128, 160]', '"levels": [96, Infinity, 160]');
            tempFile = fullfile(tempDir, 'config.json');
            fid = fopen(tempFile, 'w');
            fprintf(fid, '%s', rawCfg);
            fclose(fid);

            try
                load_compiler_config(tempFile);
                testCase.fail('Expected error for non-finite levels');
            catch ME
                testCase.assertEqual(ME.identifier, testCase.ERROR_ID);
                testCase.verifyTrue(contains(ME.message, 'levels'));
            end
        end

        %% ===== v4 negative tests: type strictness =====

        function testNonLogicalBooleanRejected(testCase)
            % Verify mesh_qc.self_intersect_check = [1, 0] (numeric) is rejected
            tempFile = [tempname '.json'];
            cleanupObj = onCleanup(@() TestBootstrap.deleteFile(tempFile));

            data = TestBootstrap.loadExampleConfig(testCase.BaseDir);
            data.mesh_qc.self_intersect_check = [1, 0];
            TestBootstrap.writeJson(tempFile, data);

            try
                load_compiler_config(tempFile);
                testCase.fail('Expected error for non-logical boolean');
            catch ME
                testCase.assertEqual(ME.identifier, testCase.ERROR_ID);
                testCase.verifyTrue(contains(ME.message, 'logical'));
            end
        end

        function testNonFiniteBoundRejected(testCase)
            % Verify bounds with Infinity value is rejected
            tempDir = tempname;
            mkdir(tempDir);
            cleanupDir = onCleanup(@() TestBootstrap.deleteDir(tempDir));

            srcDesc = fullfile(testCase.BaseDir, 'configs', 'descriptor_definition.json');
            copyfile(srcDesc, fullfile(tempDir, 'descriptor_definition.json'));

            srcCfg = fullfile(testCase.BaseDir, 'configs', 'compiler_config.example.json');
            rawCfg = fileread(srcCfg);
            rawCfg = strrep(rawCfg, '0.03', 'Infinity');
            tempFile = fullfile(tempDir, 'config.json');
            fid = fopen(tempFile, 'w');
            fprintf(fid, '%s', rawCfg);
            fclose(fid);

            try
                load_compiler_config(tempFile);
                testCase.fail('Expected error for non-finite bound');
            catch ME
                testCase.assertEqual(ME.identifier, testCase.ERROR_ID);
                testCase.verifyTrue(contains(ME.message, 'bounds'));
            end
        end

        function testNonScalarNumericRejected(testCase)
            % Verify reference_length_mm = [1, 2] (non-scalar) is rejected
            tempFile = [tempname '.json'];
            cleanupObj = onCleanup(@() TestBootstrap.deleteFile(tempFile));

            data = TestBootstrap.loadExampleConfig(testCase.BaseDir);
            data.reference_length_mm = [1, 2];
            TestBootstrap.writeJson(tempFile, data);

            try
                load_compiler_config(tempFile);
                testCase.fail('Expected error for non-scalar reference_length_mm');
            catch ME
                testCase.assertEqual(ME.identifier, testCase.ERROR_ID);
                testCase.verifyTrue(contains(ME.message, 'reference_length_mm'));
            end
        end

        function testNonexistentConfigFileRejected(testCase)
            % Verify nonexistent config file throws MATLABGyroid:InvalidConfig
            try
                load_compiler_config(fullfile(tempname, 'nonexistent.json'));
                testCase.fail('Expected error for nonexistent file');
            catch ME
                testCase.assertEqual(ME.identifier, testCase.ERROR_ID);
            end
        end

    end

    methods (Static, Access = private)
        function deleteFile(filePath)
            if exist(filePath, 'file')
                delete(filePath);
            end
        end

        function deleteDir(dirPath)
            if exist(dirPath, 'dir')
                rmdir(dirPath, 's');
            end
        end

        function data = loadExampleConfig(baseDir)
            configPath = fullfile(baseDir, 'configs', 'compiler_config.example.json');
            raw = fileread(configPath);
            data = jsondecode(raw);
        end

        function writeJson(filePath, data)
            fid = fopen(filePath, 'w');
            fprintf(fid, '%s', jsonencode(data));
            fclose(fid);
        end
    end
end
