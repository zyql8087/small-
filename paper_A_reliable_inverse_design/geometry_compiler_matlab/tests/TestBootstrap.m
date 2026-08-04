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
            expectedVersion = 'matlab-gyroid-0.2.0';
            actualVersion = compiler_version();
            testCase.assertEqual(actualVersion, expectedVersion);
        end

        function testM03ContinuousCsgContract(testCase)
            contract = compiler_contract();
            testCase.verifyEqual(contract.geometryDefinition, ...
                'continuous_sheet_gyroid_intersect_hard_box');
            testCase.verifyEqual(contract.validationStage, ...
                'M03_GEOMETRY_MESH');
            testCase.verifyEqual(contract.betaBox, 1.0);
            testCase.verifyEqual(contract.isosurfaceLevel, 0.0);
            testCase.verifyEqual(contract.gridConvention, ...
                'cell_centered_half_step_exterior');
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
            try
                bwdist(false(10, 10, 10));
            catch
                testCase.verifyTrue(false, 'Image Processing Toolbox is mandatory');
                return;
            end

            essential_funcs = {'bwdist', 'bwconncomp', 'bwskel', 'padarray'};
            for i = 1:length(essential_funcs)
                funcExists = exist(essential_funcs{i}, 'file');
                testCase.assertTrue(funcExists ~= 0, ...
                    sprintf('Function "%s" must be available', essential_funcs{i}));
            end
        end

        %% ===== Negative tests: JSON and field presence =====

        function testInvalidJsonRejected(testCase)
            % Verify malformed JSON throws MATLABGyroid:InvalidConfig with message
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
                testCase.verifyTrue(contains(ME.message, 'JSON parsing'), ...
                    'Error message should mention JSON parsing');
                testCase.verifyEqual(numel(ME.cause), 1, ...
                    'JSON parsing error must preserve its original cause');
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
            fixture = TestBootstrap.createFixture(testCase.BaseDir);
            fixture.data.descriptor_names = {"areaMean", "relativeVolume", "relativeArea", "thickness", "poreDiameter"};
            TestBootstrap.expectConfigError(testCase, fixture, 'Descriptor order');
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
            fixture = TestBootstrap.createFixture(testCase.BaseDir);
            fixture.data.method_bounds = 1;
            TestBootstrap.expectConfigError(testCase, fixture, 'method_bounds');
        end

        function testInvalidMeshQcTypeRejected(testCase)
            fixture = TestBootstrap.createFixture(testCase.BaseDir);
            fixture.data.mesh_qc = 1;
            TestBootstrap.expectConfigError(testCase, fixture, 'mesh_qc');
        end

        %% ===== Negative tests: method_bounds structure =====

        function testMissingMethodRejected(testCase)
            fixture = TestBootstrap.createFixture(testCase.BaseDir);
            fixture.data.method_bounds = rmfield(fixture.data.method_bounds, 'M2');
            TestBootstrap.expectConfigError(testCase, fixture, 'M2');
        end

        function testInvalidBoundsNestedStructureRejected(testCase)
            fixture = TestBootstrap.createFixture(testCase.BaseDir);
            fixture.data.method_bounds.M1.bounds.c0 = 0.5;
            TestBootstrap.expectConfigError(testCase, fixture, 'bounds');
        end

        function testLowerGreaterThanUpperRejected(testCase)
            fixture = TestBootstrap.createFixture(testCase.BaseDir);
            fixture.data.method_bounds.M1.bounds.c0.lower = 0.95;
            fixture.data.method_bounds.M1.bounds.c0.upper = 0.10;
            TestBootstrap.expectConfigError(testCase, fixture, 'lower');
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

        function testDescriptorOrderMutationRejectedByFrozenHash(testCase)
            tempDir = tempname;
            mkdir(tempDir);
            cleanupDir = onCleanup(@() TestBootstrap.deleteDir(tempDir));
            copyfile(fullfile(testCase.BaseDir, 'configs', 'parameter_domain_manifest.json'), ...
                fullfile(tempDir, 'parameter_domain_manifest.json'));
            badDescJson = ['{"schema_version":"1.0","descriptors":[' ...
                '{"name":"relativeArea","formula":"x","units":"mm","computation_method":"x"},' ...
                '{"name":"relativeVolume","formula":"x","units":"mm","computation_method":"x"},' ...
                '{"name":"thickness","formula":"x","units":"mm","computation_method":"x"},' ...
                '{"name":"poreDiameter","formula":"x","units":"mm","computation_method":"x"},' ...
                '{"name":"areaMean","formula":"x","units":"mm","computation_method":"x"}' ...
                ']}'];
            badDescPath = fullfile(tempDir, 'descriptor_definition.json');
            fid = fopen(badDescPath, 'w'); fprintf(fid, '%s', badDescJson); fclose(fid);
            data = TestBootstrap.loadExampleConfig(testCase.BaseDir);
            data.descriptor_definition_path = 'descriptor_definition.json';
            data.descriptor_definition_sha256 = lower(char(string( ...
                sha256_file(badDescPath, testCase.ERROR_ID, 'test'))));
            tempFile = fullfile(tempDir, 'config.json');
            TestBootstrap.writeJson(tempFile, data);
            try
                load_compiler_config(tempFile);
                testCase.fail('Expected frozen-hash rejection for descriptor mutation');
            catch ME
                testCase.assertEqual(ME.identifier, testCase.ERROR_ID);
                testCase.verifyTrue(contains(ME.message, ...
                    'descriptor_definition_sha256 does not match frozen contract value'));
            end
        end

        function testDescriptorSchemaMutationRejectedByFrozenHash(testCase)
            tempDir = tempname;
            mkdir(tempDir);
            cleanupDir = onCleanup(@() TestBootstrap.deleteDir(tempDir));
            copyfile(fullfile(testCase.BaseDir, 'configs', 'parameter_domain_manifest.json'), ...
                fullfile(tempDir, 'parameter_domain_manifest.json'));
            srcDesc = fullfile(testCase.BaseDir, 'configs', 'descriptor_definition.json');
            raw = fileread(srcDesc);
            raw = strrep(raw, '"schema_version": "1.0"', '"schema_version": "2.0"');
            badDescPath = fullfile(tempDir, 'descriptor_definition.json');
            fid = fopen(badDescPath, 'w'); fprintf(fid, '%s', raw); fclose(fid);
            data = TestBootstrap.loadExampleConfig(testCase.BaseDir);
            data.descriptor_definition_path = 'descriptor_definition.json';
            data.descriptor_definition_sha256 = lower(char(string( ...
                sha256_file(badDescPath, testCase.ERROR_ID, 'test'))));
            tempFile = fullfile(tempDir, 'config.json');
            TestBootstrap.writeJson(tempFile, data);
            try
                load_compiler_config(tempFile);
                testCase.fail('Expected frozen-hash rejection for descriptor mutation');
            catch ME
                testCase.assertEqual(ME.identifier, testCase.ERROR_ID);
                testCase.verifyTrue(contains(ME.message, ...
                    'descriptor_definition_sha256 does not match frozen contract value'));
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

            % M2: c_projected in [0.03, 0.20], w in (2,8)
            m2 = config.method_bounds.M2;
            testCase.assertEqual(m2.bounds.c_projected.lower, 0.03);
            testCase.assertEqual(m2.bounds.c_projected.upper, 0.20);
            testCase.assertEqual(m2.bounds.w.lower, 2.0);
            testCase.assertEqual(m2.bounds.w.upper, 8.0);

            % M3: c0,c1,c2 in [0.03, 0.20], w in (2,8)
            m3 = config.method_bounds.M3;
            testCase.assertEqual(m3.bounds.c0.lower, 0.03);
            testCase.assertEqual(m3.bounds.c0.upper, 0.20);
            testCase.assertEqual(m3.bounds.w.lower, 2.0);
            testCase.assertEqual(m3.bounds.w.upper, 8.0);
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
            testCase.assertEqual(gp.Lx_over_l, 1.0);
            testCase.assertEqual(gp.Ly_over_l, 1.0);
            testCase.assertEqual(gp.Lz0_over_l, 1.5);
            testCase.assertEqual(char(string(gp.output_units)), 'mm');
        end

        %% ===== v4 negative tests: geometry_parameters =====

        function testMissingGeometryParametersRejected(testCase)
            fixture = TestBootstrap.createFixture(testCase.BaseDir);
            fixture.data = rmfield(fixture.data, 'geometry_parameters');
            TestBootstrap.expectConfigError(testCase, fixture, 'geometry_parameters');
        end

        function testInvalidGeometryParametersTypeRejected(testCase)
            fixture = TestBootstrap.createFixture(testCase.BaseDir);
            fixture.data.geometry_parameters = 'bad';
            TestBootstrap.expectConfigError(testCase, fixture, 'geometry_parameters');
        end

        %% ===== v4 negative tests: active_variables / fixed_variables / projection =====

        function testIllegalActiveVariableRejected(testCase)
            fixture = TestBootstrap.createFixture(testCase.BaseDir);
            fixture.data.method_bounds.M1.active_variables = {"banana"};
            TestBootstrap.expectConfigError(testCase, fixture, 'illegal variable');
        end

        function testMissingFixedVariablesRejected(testCase)
            fixture = TestBootstrap.createFixture(testCase.BaseDir);
            fixture.data.method_bounds.M1 = rmfield(fixture.data.method_bounds.M1, 'fixed_variables');
            TestBootstrap.expectConfigError(testCase, fixture, 'fixed_variables');
        end

        function testMissingProjectionInM2Rejected(testCase)
            fixture = TestBootstrap.createFixture(testCase.BaseDir);
            fixture.data.method_bounds.M2 = rmfield(fixture.data.method_bounds.M2, 'projection');
            TestBootstrap.expectConfigError(testCase, fixture, 'M2.projection');
        end

        %% ===== v4 negative tests: levels validation =====

        function testEmptyLevelsRejected(testCase)
            fixture = TestBootstrap.createFixture(testCase.BaseDir);
            fixture.data.method_bounds.M1.levels = [];
            TestBootstrap.expectConfigError(testCase, fixture, 'levels');
        end

        function testNonIncreasingLevelsRejected(testCase)
            fixture = TestBootstrap.createFixture(testCase.BaseDir);
            fixture.data.method_bounds.M1.levels = [128, 96, 160];
            TestBootstrap.expectConfigError(testCase, fixture, 'levels');
        end

        function testNonIntegerLevelsRejected(testCase)
            fixture = TestBootstrap.createFixture(testCase.BaseDir);
            fixture.data.method_bounds.M1.levels = [96, 128.5, 160];
            TestBootstrap.expectConfigError(testCase, fixture, 'levels');
        end

        function testNonFiniteLevelsRejected(testCase)
            tempDir = tempname;
            mkdir(tempDir);
            cleanupDir = onCleanup(@() TestBootstrap.deleteDir(tempDir));
            copyfile(fullfile(testCase.BaseDir, 'configs', 'descriptor_definition.json'), ...
                fullfile(tempDir, 'descriptor_definition.json'));
            copyfile(fullfile(testCase.BaseDir, 'configs', 'parameter_domain_manifest.json'), ...
                fullfile(tempDir, 'parameter_domain_manifest.json'));
            srcCfg = fullfile(testCase.BaseDir, 'configs', 'compiler_config.example.json');
            rawCfg = fileread(srcCfg);
            rawCfg = strrep(rawCfg, '"levels": [96, 128, 160]', '"levels": [96, Infinity, 160]');
            tempFile = fullfile(tempDir, 'config.json');
            fid = fopen(tempFile, 'w'); fprintf(fid, '%s', rawCfg); fclose(fid);
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
            fixture = TestBootstrap.createFixture(testCase.BaseDir);
            fixture.data.mesh_qc.self_intersect_check = [1, 0];
            TestBootstrap.expectConfigError(testCase, fixture, 'logical');
        end

        function testNonFiniteBoundRejected(testCase)
            tempDir = tempname;
            mkdir(tempDir);
            cleanupDir = onCleanup(@() TestBootstrap.deleteDir(tempDir));
            copyfile(fullfile(testCase.BaseDir, 'configs', 'descriptor_definition.json'), ...
                fullfile(tempDir, 'descriptor_definition.json'));
            copyfile(fullfile(testCase.BaseDir, 'configs', 'parameter_domain_manifest.json'), ...
                fullfile(tempDir, 'parameter_domain_manifest.json'));
            srcCfg = fullfile(testCase.BaseDir, 'configs', 'compiler_config.example.json');
            rawCfg = fileread(srcCfg);
            rawCfg = strrep(rawCfg, '0.03', 'Infinity');
            tempFile = fullfile(tempDir, 'config.json');
            fid = fopen(tempFile, 'w'); fprintf(fid, '%s', rawCfg); fclose(fid);
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
            try
                load_compiler_config(fullfile(tempname, 'nonexistent.json'));
                testCase.fail('Expected error for nonexistent file');
            catch ME
                testCase.assertEqual(ME.identifier, testCase.ERROR_ID);
                testCase.verifyTrue(contains(ME.message, 'not found'), ...
                    'Error message should indicate file not found');
            end
        end

        %% ===== v5 Step 4: Boundary tests for public input =====

        function testNoArgumentsRejected(testCase)
            try
                load_compiler_config();
                testCase.fail('Expected error for no arguments');
            catch ME
                testCase.assertEqual(ME.identifier, testCase.ERROR_ID);
                testCase.verifyTrue(contains(ME.message, 'exactly one config_path'));
            end
        end

        function testNumericPathRejected(testCase)
            try
                load_compiler_config(1);
                testCase.fail('Expected error for numeric path');
            catch ME
                testCase.assertEqual(ME.identifier, testCase.ERROR_ID);
                testCase.verifyTrue(contains(ME.message, 'config_path'));
            end
        end

        function testStringArrayPathRejected(testCase)
            try
                load_compiler_config(["a", "b"]);
                testCase.fail('Expected error for string array path');
            catch ME
                testCase.assertEqual(ME.identifier, testCase.ERROR_ID);
                testCase.verifyTrue(contains(ME.message, 'config_path'));
            end
        end

        function testMissingDescriptorFileRejected(testCase)
            fixture = TestBootstrap.createFixture(testCase.BaseDir);
            delete(fullfile(fixture.dir, 'descriptor_definition.json'));
            TestBootstrap.expectConfigError(testCase, fixture, 'Descriptor definition not found');
        end

        function testMissingManifestFileRejected(testCase)
            fixture = TestBootstrap.createFixture(testCase.BaseDir);
            delete(fullfile(fixture.dir, 'parameter_domain_manifest.json'));
            TestBootstrap.expectConfigError(testCase, fixture, 'Parameter-domain manifest not found');
        end

        function testResolutionOverflowRejected(testCase)
            fixture = TestBootstrap.createFixture(testCase.BaseDir);
            fixture.data.resolution = 2^32;
            TestBootstrap.expectConfigError(testCase, fixture, 'uint32 capacity');
        end

        %% ===== v5 Step 5: mesh-QC range tests =====

        function testMeshQcEdgeRatioTooLargeRejected(testCase)
            fixture = TestBootstrap.createFixture(testCase.BaseDir);
            fixture.data.mesh_qc.min_edge_length_ratio = 1.1;
            TestBootstrap.expectConfigError(testCase, fixture, 'min_edge_length_ratio');
        end

        function testMeshQcAngleTooLargeRejected(testCase)
            fixture = TestBootstrap.createFixture(testCase.BaseDir);
            fixture.data.mesh_qc.max_angle_deviations = 181;
            TestBootstrap.expectConfigError(testCase, fixture, 'max_angle_deviations');
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

        function fixture = createFixture(baseDir)
            fixture.dir = tempname;
            mkdir(fixture.dir);
            fixture.cleanup = onCleanup(@() TestBootstrap.deleteDir(fixture.dir));
            copyfile(fullfile(baseDir, 'configs', 'descriptor_definition.json'), ...
                fullfile(fixture.dir, 'descriptor_definition.json'));
            copyfile(fullfile(baseDir, 'configs', 'parameter_domain_manifest.json'), ...
                fullfile(fixture.dir, 'parameter_domain_manifest.json'));
            fixture.data = TestBootstrap.loadExampleConfig(baseDir);
            fixture.configPath = fullfile(fixture.dir, 'compiler_config.json');
        end

        function expectConfigError(testCase, fixture, expectedMsgFragment)
            TestBootstrap.writeJson(fixture.configPath, fixture.data);
            try
                load_compiler_config(fixture.configPath);
                testCase.fail(sprintf('Expected error containing "%s"', expectedMsgFragment));
            catch ME
                testCase.assertEqual(ME.identifier, testCase.ERROR_ID);
                testCase.verifyTrue(contains(ME.message, expectedMsgFragment));
            end
        end
    end
end
