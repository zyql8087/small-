classdef TestContractHardening < matlab.unittest.TestCase
    properties (Constant, Access = private)
        ErrorId = 'MATLABGyroid:InvalidConfig'
    end

    properties (Access = private)
        BaseDir
    end

    methods (TestClassSetup)
        function setupClass(testCase)
            testFile = mfilename('fullpath');
            testCase.BaseDir = fileparts(fileparts(testFile));
            addpath(fullfile(testCase.BaseDir, 'core'));
        end
    end

    methods (Test)
        function testMapsDescriptorContractMismatchSeparately(testCase)
            testCase.verifyEqual(map_m04_failure_code( ...
                'MATLABGyroid:DescriptorContractMismatch'), ...
                'DESCRIPTOR_CONTRACT_MISMATCH');
            testCase.verifyEqual(map_m04_failure_code( ...
                'MATLABGyroid:DescriptorProfileInvalid'), ...
                'DESCRIPTOR_PROFILE_INVALID');
        end

        function testParameterManifestExistsAndMatchesSmallSources(testCase)
            path = fullfile(testCase.BaseDir, 'configs', ...
                'parameter_domain_manifest.json');
            testCase.assertEqual(exist(path, 'file'), 2);
            manifest = jsondecode(fileread(path));
            testCase.verifyEqual(char(string(manifest.schema_version)), '1.0');
            testCase.verifyEqual(manifest.methods.M1.row_counts.pooled, 7115);
            testCase.verifyEqual(manifest.methods.M2.row_counts.pooled, 9550);
            testCase.verifyEqual(manifest.methods.M3.row_counts.pooled, 8890);
            testCase.verifyEqual(char(string(manifest.methods.M3.sheet)), 'class12');
            testCase.verifyEqual(manifest.methods.M2.observed.w.lower, 2.0019789, ...
                'AbsTol', 1e-12);
            testCase.verifyEqual(manifest.methods.M2.observed.w.upper, 7.998, ...
                'AbsTol', 1e-12);
            testCase.verifyEqual(manifest.methods.M3.observed.w.lower, 2.0046, ...
                'AbsTol', 1e-12);
            testCase.verifyEqual(manifest.methods.M3.observed.w.upper, 7.995, ...
                'AbsTol', 1e-12);
        end

        function testCanonicalBoundsAndPublishedProfile(testCase)
            config = load_compiler_config(fullfile(testCase.BaseDir, 'configs', ...
                'compiler_config.example.json'));
            testCase.verifyEqual(config.method_bounds.M1.fixed_variables.w, 0);
            testCase.verifyEqual(config.method_bounds.M2.bounds.w.lower, 2.0);
            testCase.verifyEqual(config.method_bounds.M2.bounds.w.upper, 8.0);
            testCase.verifyFalse(config.method_bounds.M2.bounds.w.lower_inclusive);
            testCase.verifyFalse(config.method_bounds.M2.bounds.w.upper_inclusive);
            testCase.verifyEqual(config.method_bounds.M3.bounds.w.lower, 2.0);
            testCase.verifyEqual(config.method_bounds.M3.bounds.w.upper, 8.0);
            testCase.verifyEqual(char(string(config.geometry_parameters.cell_size_profile)), ...
                'gamma(z)=1.5+z/w');
        end

        function testFiniteNormalizedDomainIsExplicit(testCase)
            config = load_compiler_config(fullfile(testCase.BaseDir, 'configs', ...
                'compiler_config.example.json'));
            domain = config.geometry_parameters.domain_over_l;
            testCase.verifyEqual(domain.x(:)', [0, 1]);
            testCase.verifyEqual(domain.y(:)', [0, 1]);
            testCase.verifyEqual(domain.z(:)', [0, 2]);
            testCase.verifyEqual(char(string(config.geometry_parameters.coordinate_units)), ...
                'normalized_by_reference_length');
            testCase.verifyEqual(char(string(config.geometry_parameters.output_units)), 'mm');
        end

        function testAllMethodsContainRequiredConvergenceLevels(testCase)
            config = load_compiler_config(fullfile(testCase.BaseDir, 'configs', ...
                'compiler_config.example.json'));
            required = [96, 128, 160];
            names = {'M1', 'M2', 'M3'};
            for i = 1:numel(names)
                levels = double(config.method_bounds.(names{i}).levels(:)');
                testCase.verifyTrue(all(ismember(required, levels)), ...
                    sprintf('%s must contain 96,128,160', names{i}));
            end
        end

        function testV1CandidateDescriptorDefinitionRemainsAuditable(testCase)
            path = fullfile(testCase.BaseDir, 'configs', ...
                'descriptor_definition.v1_candidate.json');
            definition = jsondecode(fileread(path));
            testCase.verifyEqual(char(string(definition.validation_status)), ...
                'candidate_pending_gate0');
            testCase.verifyEqual(char(string(definition.grid_convention.spacing_policy)), ...
                'isotropic_required');
            testCase.verifyEqual(definition.finite_domain_boundary_policy.void_connectivity_3d, 26);
            testCase.verifyEqual(definition.finite_domain_boundary_policy.slice_connectivity_2d, 8);
        end

        function testProtectedContractJsonFilesUseLfAndMatchHashes(testCase)
            configDir = fullfile(testCase.BaseDir, 'configs');
            configEntries = dir(fullfile(configDir, '*.json'));
            protectedFiles = sort({configEntries.name});
            testCase.assertNotEmpty(protectedFiles, ...
                'No protected contract JSON files were found.');
            for i = 1:numel(protectedFiles)
                path = fullfile(configDir, protectedFiles{i});
                fileId = fopen(path, 'rb');
                testCase.assertNotEqual(fileId, -1, ...
                    sprintf('Cannot open protected contract JSON: %s', path));
                cleanup = onCleanup(@() fclose(fileId));
                bytes = fread(fileId, Inf, '*uint8');
                clear cleanup;
                testCase.verifyFalse(any(bytes == uint8(13)), ...
                    sprintf('%s must use LF-only line endings.', protectedFiles{i}));
            end

            relativePaths = cellfun(@(name) strrep( ...
                fullfile('configs', name), '\', '/'), protectedFiles, ...
                'UniformOutput', false);
            quotedPaths = cellfun(@(path) ['"' path '"'], relativePaths, ...
                'UniformOutput', false);
            command = sprintf('git -C "%s" check-attr text eol -- %s', ...
                testCase.BaseDir, strjoin(quotedPaths, ' '));
            [status, output] = system(command);
            testCase.assertEqual(status, 0, sprintf( ...
                'git check-attr failed: %s', strtrim(output)));
            attributeLines = regexp(strtrim(output), '\r?\n', 'split');
            attributeLines = cellfun(@strtrim, attributeLines, ...
                'UniformOutput', false);
            for i = 1:numel(relativePaths)
                path = relativePaths{i};
                testCase.verifyTrue(any(strcmp(attributeLines, ...
                    [path ': text: set'])), ...
                    sprintf('%s must resolve Git text=set.', path));
                testCase.verifyTrue(any(strcmp(attributeLines, ...
                    [path ': eol: lf'])), ...
                    sprintf('%s must resolve Git eol=lf.', path));
            end

            config = jsondecode(fileread(fullfile(configDir, ...
                'compiler_config.example.json')));
            manifestHash = sha256_file(fullfile(configDir, ...
                'parameter_domain_manifest.json'), testCase.ErrorId, ...
                'parameter-domain manifest');
            descriptorHash = sha256_file(fullfile(configDir, ...
                'descriptor_definition.v2.json'), testCase.ErrorId, ...
                'descriptor definition');
            testCase.verifyEqual(manifestHash, ...
                lower(char(string(config.parameter_domain_manifest_sha256))));
            testCase.verifyEqual(descriptorHash, ...
                lower(char(string(config.descriptor_definition_sha256))));
        end

        %% ===== 7.1 Step 2: Method-semantics mutation tests =====

        function testM1ActiveSetRejected(testCase)
            fixture = TestContractHardening.createFixture(testCase.BaseDir);
            fixture.data.method_bounds.M1.active_variables = {"c0", "c1"};
            TestContractHardening.verifyInvalid(testCase, fixture, 'M1.active_variables');
        end

        function testM1NonzeroWRejected(testCase)
            fixture = TestContractHardening.createFixture(testCase.BaseDir);
            fixture.data.method_bounds.M1.fixed_variables.w = 7;
            TestContractHardening.verifyInvalid(testCase, fixture, 'M1.fixed_variables.w');
        end

        function testM1ProjectionRejected(testCase)
            fixture = TestContractHardening.createFixture(testCase.BaseDir);
            fixture.data.method_bounds.M1.projection = struct('type', 'bogus');
            TestContractHardening.verifyInvalid(testCase, fixture, 'M1.projection');
        end

        function testM1BoundsSetRejected(testCase)
            fixture = TestContractHardening.createFixture(testCase.BaseDir);
            fixture.data.method_bounds.M1.bounds = rmfield(fixture.data.method_bounds.M1.bounds, 'c2');
            TestContractHardening.verifyInvalid(testCase, fixture, 'M1.bounds');
        end

        function testM2ActiveSetRejected(testCase)
            fixture = TestContractHardening.createFixture(testCase.BaseDir);
            fixture.data.method_bounds.M2.active_variables = {"w"};
            TestContractHardening.verifyInvalid(testCase, fixture, 'M2.active_variables');
        end

        function testM2MissingProjectionRejected(testCase)
            fixture = TestContractHardening.createFixture(testCase.BaseDir);
            fixture.data.method_bounds.M2 = rmfield(fixture.data.method_bounds.M2, 'projection');
            TestContractHardening.verifyInvalid(testCase, fixture, 'M2.projection');
        end

        function testM2ProjectionTypeRejected(testCase)
            fixture = TestContractHardening.createFixture(testCase.BaseDir);
            fixture.data.method_bounds.M2.projection.type = 'bogus';
            TestContractHardening.verifyInvalid(testCase, fixture, 'M2.projection.type');
        end

        function testM2ProjectionVariablesRejected(testCase)
            fixture = TestContractHardening.createFixture(testCase.BaseDir);
            fixture.data.method_bounds.M2.projection.variables = {"w"};
            TestContractHardening.verifyInvalid(testCase, fixture, 'M2.projection.variables');
        end

        function testM2ProjectedNameRejected(testCase)
            fixture = TestContractHardening.createFixture(testCase.BaseDir);
            fixture.data.method_bounds.M2.projection.projected_name = 'c0';
            TestContractHardening.verifyInvalid(testCase, fixture, 'M2.projection.projected_name');
        end

        function testM2ProjectionFormulaRejected(testCase)
            fixture = TestContractHardening.createFixture(testCase.BaseDir);
            fixture.data.method_bounds.M2.projection.formula = 'c0';
            TestContractHardening.verifyInvalid(testCase, fixture, 'M2.projection.formula');
        end

        function testM2FixedVariablesRejected(testCase)
            fixture = TestContractHardening.createFixture(testCase.BaseDir);
            fixture.data.method_bounds.M2.fixed_variables.w = 0;
            TestContractHardening.verifyInvalid(testCase, fixture, 'M2.fixed_variables');
        end

        function testM2BoundsSetRejected(testCase)
            fixture = TestContractHardening.createFixture(testCase.BaseDir);
            fixture.data.method_bounds.M2.bounds = rmfield(fixture.data.method_bounds.M2.bounds, 'c_projected');
            TestContractHardening.verifyInvalid(testCase, fixture, 'M2.bounds');
        end

        function testM3ActiveSetRejected(testCase)
            fixture = TestContractHardening.createFixture(testCase.BaseDir);
            fixture.data.method_bounds.M3.active_variables = {"c0"};
            TestContractHardening.verifyInvalid(testCase, fixture, 'M3.active_variables');
        end

        function testM3FixedVariablesRejected(testCase)
            fixture = TestContractHardening.createFixture(testCase.BaseDir);
            fixture.data.method_bounds.M3.fixed_variables.w = 0;
            TestContractHardening.verifyInvalid(testCase, fixture, 'M3.fixed_variables');
        end

        function testM3ProjectionRejected(testCase)
            fixture = TestContractHardening.createFixture(testCase.BaseDir);
            fixture.data.method_bounds.M3.projection = struct('type', 'bogus');
            TestContractHardening.verifyInvalid(testCase, fixture, 'M3.projection');
        end

        function testM3BoundsSetRejected(testCase)
            fixture = TestContractHardening.createFixture(testCase.BaseDir);
            fixture.data.method_bounds.M3.bounds = rmfield(fixture.data.method_bounds.M3.bounds, 'w');
            TestContractHardening.verifyInvalid(testCase, fixture, 'M3.bounds');
        end

        %% ===== 7.1 Step 3: Bounds/provenance mutation tests =====

        function testM2ZeroToTwoPointFiveWRejected(testCase)
            fixture = TestContractHardening.createFixture(testCase.BaseDir);
            fixture.data.method_bounds.M2.bounds.w.lower = 0;
            fixture.data.method_bounds.M2.bounds.w.upper = 2.5;
            TestContractHardening.verifyInvalid(testCase, fixture, 'M2.bounds.w');
        end

        function testClass3ProvenanceRejected(testCase)
            fixture = TestContractHardening.createFixture(testCase.BaseDir);
            fixture.data.method_bounds.M3.bounds_manifest_method = 'class3';
            TestContractHardening.verifyInvalid(testCase, fixture, 'M3.bounds_manifest_method');
        end

        function testSingleResolutionLevelRejected(testCase)
            fixture = TestContractHardening.createFixture(testCase.BaseDir);
            fixture.data.method_bounds.M3.levels = 128;
            TestContractHardening.verifyInvalid(testCase, fixture, 'M3.levels');
        end

        %% ===== 7.1 Step 4: Hash mutation tests =====

        function testDescriptorSemanticMutationRejectedByHash(testCase)
            fixture = TestContractHardening.createFixture(testCase.BaseDir);
            path = fullfile(fixture.dir, 'descriptor_definition.v2.json');
            definition = jsondecode(fileread(path));
            definition.profiles(2).algorithms.areaMean = ...
                'unexpected_area_algorithm';
            TestContractHardening.writeJson(path, definition);
            TestContractHardening.verifyInvalid(testCase, fixture, 'descriptor_definition_sha256');
        end

        function testParameterManifestMutationRejectedByHash(testCase)
            fixture = TestContractHardening.createFixture(testCase.BaseDir);
            path = fullfile(fixture.dir, 'parameter_domain_manifest.json');
            manifest = jsondecode(fileread(path));
            manifest.methods.M2.compiler_bounds.w.lower = 0;
            TestContractHardening.writeJson(path, manifest);
            TestContractHardening.verifyInvalid(testCase, fixture, 'parameter_domain_manifest_sha256');
        end

        %% ===== v6 P1 regression: inclusivity required =====

        function testMissingInclusivityFieldsRejected(testCase)
            fixture = TestContractHardening.createFixture(testCase.BaseDir);
            fixture.data.method_bounds.M2.bounds.w = struct('lower', 2.0, 'upper', 8.0); % missing inclusivity
            TestContractHardening.verifyInvalid(testCase, fixture, ...
                'method_bounds.M2.bounds.w must have fields')
        end

        function testNonLogicalInclusivityRejected(testCase)
            fixture = TestContractHardening.createFixture(testCase.BaseDir);
            % Use a true vector (1x2) not scalar - [true] is still isscalar=true
            fixture.data.method_bounds.M2.bounds.w.lower_inclusive = [true, false]; % true vector
            fixture.data.method_bounds.M2.bounds.w.upper_inclusive = [true, false]; % true vector
            TestContractHardening.verifyInvalid(testCase, fixture, '.lower_inclusive must be a logical scalar')
        end

        %% ===== v6 P1 regression: geometry parameters strict =====

        function testNaNGeometryScaleRejected(testCase)
            fixture = TestContractHardening.createFixture(testCase.BaseDir);
            fixture.data.geometry_parameters.Lx_over_l = NaN;
            TestContractHardening.verifyInvalid(testCase, fixture, 'Lx_over_l must be a finite positive numeric scalar')
        end

        function testInfGeometryScaleRejected(testCase)
            fixture = TestContractHardening.createFixture(testCase.BaseDir);
            fixture.data.geometry_parameters.Ly_over_l = Inf;
            TestContractHardening.verifyInvalid(testCase, fixture, 'Ly_over_l must be a finite positive numeric scalar')
        end

        function testVectorGeometryScaleRejected(testCase)
            fixture = TestContractHardening.createFixture(testCase.BaseDir);
            fixture.data.geometry_parameters.Lz0_over_l = [1.5, 1.5];
            TestContractHardening.verifyInvalid(testCase, fixture, 'Lz0_over_l must be a finite positive numeric scalar')
        end

        function testStringGeometryScaleRejected(testCase)
            fixture = TestContractHardening.createFixture(testCase.BaseDir);
            fixture.data.geometry_parameters.Lx_over_l = 'wrong';
            TestContractHardening.verifyInvalid(testCase, fixture, 'Lx_over_l must be a finite positive numeric scalar')
        end

        function testWrongPhysicalConversionRejected(testCase)
            fixture = TestContractHardening.createFixture(testCase.BaseDir);
            fixture.data.geometry_parameters.physical_conversion = 'apply scaling twice';
            TestContractHardening.verifyInvalid(testCase, fixture, 'physical_conversion')
        end

        %% ===== v6 P1 regression: immutable contract + type safety =====

        function testProjectionVariablesNumericRejected(testCase)
            fixture = TestContractHardening.createFixture(testCase.BaseDir);
            fixture.data.method_bounds.M2.projection.variables = 123; % numeric, not string/cell
            TestContractHardening.verifyInvalid(testCase, fixture, '.variables must be a string/cell array')
        end

        function testCoordinatedTamperingRejectedByFrozenHash(testCase)
            fixture = TestContractHardening.createFixture(testCase.BaseDir);
            % Modify descriptor AND update config hash simultaneously
            path = fullfile(fixture.dir, 'descriptor_definition.v2.json');
            def = jsondecode(fileread(path));
            def.profiles(1).algorithms.areaMean = 'bogus';
            TestContractHardening.writeJson(path, def);
            % Update config with NEW hash (computed from modified file)
            fixture.data.descriptor_definition_sha256 = lower(char(string(...
                sha256_file(fullfile(fixture.dir, 'descriptor_definition.v2.json'), ...
                testCase.ErrorId, 'test'))));
            % But frozen contract value won't match!
            TestContractHardening.verifyInvalid(testCase, fixture, 'does not match frozen contract value')
        end

        function testCoordinatedManifestTamperingRejectedByFrozenHash(testCase)
            fixture = TestContractHardening.createFixture(testCase.BaseDir);
            path = fullfile(fixture.dir, 'parameter_domain_manifest.json');
            manifest = jsondecode(fileread(path));
            manifest.methods.M2.compiler_bounds.w.lower = 0;
            TestContractHardening.writeJson(path, manifest);
            fixture.data.method_bounds.M2.bounds.w.lower = 0;
            fixture.data.parameter_domain_manifest_sha256 = sha256_file(path, ...
                testCase.ErrorId, 'test manifest');
            TestContractHardening.verifyInvalid(testCase, fixture, ...
                'does not match frozen contract value');
        end

        %% ===== v7 regression: common error boundary =====

        function testStructArrayConfigRootUsesCommonErrorId(testCase)
            fixture = TestContractHardening.createFixture(testCase.BaseDir);
            fixture.data = repmat(fixture.data, 1, 2);
            TestContractHardening.verifyInvalid(testCase, fixture, ...
                'Configuration root must be a scalar JSON object');
        end

        function testStructSchemaVersionUsesCommonErrorId(testCase)
            fixture = TestContractHardening.createFixture(testCase.BaseDir);
            fixture.data.schema_version = struct('bad', true);
            TestContractHardening.verifyInvalid(testCase, fixture, ...
                'schema_version must be a character row vector or string scalar');
        end

        function testStructPhysicalConversionUsesCommonErrorId(testCase)
            fixture = TestContractHardening.createFixture(testCase.BaseDir);
            fixture.data.geometry_parameters.physical_conversion = struct('bad', true);
            TestContractHardening.verifyInvalid(testCase, fixture, ...
                'geometry_parameters.physical_conversion must be a character row vector or string scalar');
        end

        function testStructBoundsManifestMethodUsesCommonErrorId(testCase)
            fixture = TestContractHardening.createFixture(testCase.BaseDir);
            fixture.data.method_bounds.M2.bounds_manifest_method = struct('bad', true);
            TestContractHardening.verifyInvalid(testCase, fixture, ...
                'M2.bounds_manifest_method must be a character row vector or string scalar');
        end

        function testStructDescriptorPathUsesCommonErrorId(testCase)
            fixture = TestContractHardening.createFixture(testCase.BaseDir);
            fixture.data.descriptor_definition_path = struct('bad', true);
            TestContractHardening.verifyInvalid(testCase, fixture, ...
                'descriptor_definition_path must be a character row vector or string scalar');
        end

        function testStructArrayFixedVariablesUsesCommonErrorId(testCase)
            fixture = TestContractHardening.createFixture(testCase.BaseDir);
            fixture.data.method_bounds.M1.fixed_variables = repmat( ...
                struct('w', 0), 1, 2);
            TestContractHardening.verifyInvalid(testCase, fixture, ...
                'method_bounds.M1.fixed_variables must be a scalar struct');
        end

        function testStructArrayDomainUsesCommonErrorId(testCase)
            fixture = TestContractHardening.createFixture(testCase.BaseDir);
            fixture.data.geometry_parameters.domain_over_l = repmat( ...
                fixture.data.geometry_parameters.domain_over_l, 1, 2);
            TestContractHardening.verifyInvalid(testCase, fixture, ...
                'geometry_parameters.domain_over_l must be a scalar struct');
        end

        function testExtraBoundFieldRejected(testCase)
            fixture = TestContractHardening.createFixture(testCase.BaseDir);
            fixture.data.method_bounds.M2.bounds.w.interval_semantics = 'closed';
            TestContractHardening.verifyInvalid(testCase, fixture, ...
                'method_bounds.M2.bounds.w must have fields');
        end

        function testUppercaseDeclaredHashRejected(testCase)
            fixture = TestContractHardening.createFixture(testCase.BaseDir);
            fixture.data.descriptor_definition_sha256 = upper(char(string( ...
                fixture.data.descriptor_definition_sha256)));
            TestContractHardening.verifyInvalid(testCase, fixture, ...
                'descriptor_definition_sha256 must be exactly 64 lowercase hexadecimal characters');
        end

        %% ===== v7 regression: manifest schema and preserved causes =====

        function testManifestMissingMethodsUsesCommonErrorId(testCase)
            path = fullfile(testCase.BaseDir, 'configs', ...
                'parameter_domain_manifest.json');
            manifest = jsondecode(fileread(path));
            manifest = rmfield(manifest, 'methods');
            caughtException = [];
            try
                validate_parameter_domain_manifest(manifest, testCase.ErrorId);
            catch caught
                caughtException = caught;
            end
            testCase.assertNotEmpty(caughtException);
            testCase.verifyEqual(caughtException.identifier, testCase.ErrorId);
            testCase.verifyTrue(contains(caughtException.message, ...
                'parameter_domain_manifest.methods'));
        end

        function testMalformedManifestPreservesCause(testCase)
            fixture = TestContractHardening.createFixture(testCase.BaseDir);
            path = fullfile(fixture.dir, 'parameter_domain_manifest.json');
            TestContractHardening.writeText(path, '{ malformed json ');
            hash = sha256_file(path, ...
                testCase.ErrorId, 'test manifest');
            caughtException = [];
            try
                read_hashed_json(path, hash, hash, ...
                    'parameter_domain_manifest_sha256', ...
                    'Parameter-domain manifest', testCase.ErrorId);
            catch caught
                caughtException = caught;
            end
            testCase.assertNotEmpty(caughtException);
            testCase.verifyEqual(caughtException.identifier, testCase.ErrorId);
            testCase.verifyTrue(contains(caughtException.message, ...
                'Parameter-domain manifest JSON parsing failed'));
            testCase.verifyEqual(numel(caughtException.cause), 1, ...
                'Manifest parse failure must preserve the original cause');
        end

        function testMalformedDescriptorPreservesCause(testCase)
            fixture = TestContractHardening.createFixture(testCase.BaseDir);
            path = fullfile(fixture.dir, 'descriptor_definition.v2.json');
            TestContractHardening.writeText(path, '{ malformed json ');
            hash = sha256_file(path, ...
                testCase.ErrorId, 'test descriptor');
            caughtException = [];
            try
                read_hashed_json(path, hash, hash, ...
                    'descriptor_definition_sha256', ...
                    'Descriptor definition', testCase.ErrorId);
            catch caught
                caughtException = caught;
            end
            testCase.assertNotEmpty(caughtException);
            testCase.verifyEqual(caughtException.identifier, testCase.ErrorId);
            testCase.verifyTrue(contains(caughtException.message, ...
                'Descriptor definition JSON parsing failed'));
            testCase.verifyEqual(numel(caughtException.cause), 1, ...
                'Descriptor parse failure must preserve the original cause');
        end

        %% ===== v7 regression: descriptor semantics =====

        function testV2ProfilesDeclareDistinctAreaMeanAlgorithms(testCase)
            path = fullfile(testCase.BaseDir, 'configs', ...
                'descriptor_definition.v2.json');
            definition = jsondecode(fileread(path));
            testCase.verifyEqual(definition.profiles(1).algorithms.areaMean, ...
                'mean_solid_z_slice_area');
            testCase.verifyEqual(definition.profiles(2).algorithms.areaMean, ...
                'mean_largest_void_region_over_26_z_slices');
        end

        function testDescriptorOrderValidatorIsReached(testCase)
            path = fullfile(testCase.BaseDir, 'configs', ...
                'descriptor_definition.v2.json');
            definition = jsondecode(fileread(path));
            definition.descriptor_order([1, 2]) = ...
                definition.descriptor_order([2, 1]);
            expectedNames = {'relativeVolume', 'relativeArea', 'thickness', ...
                'poreDiameter', 'areaMean'};
            caughtException = [];
            try
                validate_descriptor_definition( ...
                    definition, expectedNames, testCase.ErrorId);
            catch caught
                caughtException = caught;
            end
            testCase.assertNotEmpty(caughtException);
            testCase.verifyEqual(caughtException.identifier, testCase.ErrorId);
            testCase.verifyTrue(contains(caughtException.message, ...
                'Descriptor definition order'));
        end

        function testDescriptorSchemaValidatorIsReached(testCase)
            path = fullfile(testCase.BaseDir, 'configs', ...
                'descriptor_definition.v2.json');
            definition = jsondecode(fileread(path));
            definition.schema_version = '3.0';
            expectedNames = {'relativeVolume', 'relativeArea', 'thickness', ...
                'poreDiameter', 'areaMean'};
            caughtException = [];
            try
                validate_descriptor_definition( ...
                    definition, expectedNames, testCase.ErrorId);
            catch caught
                caughtException = caught;
            end
            testCase.assertNotEmpty(caughtException);
            testCase.verifyEqual(caughtException.identifier, testCase.ErrorId);
            testCase.verifyTrue(contains(caughtException.message, ...
                'Descriptor definition schema_version'));
        end
    end

    methods (Static, Access = private)
        function fixture = createFixture(baseDir)
            fixture.dir = tempname;
            mkdir(fixture.dir);
            fixture.cleanup = onCleanup(@() rmdir(fixture.dir, 's'));
            copyfile(fullfile(baseDir, 'configs', 'descriptor_definition.v2.json'), ...
                fullfile(fixture.dir, 'descriptor_definition.v2.json'));
            copyfile(fullfile(baseDir, 'configs', 'parameter_domain_manifest.json'), ...
                fullfile(fixture.dir, 'parameter_domain_manifest.json'));
            configPath = fullfile(baseDir, 'configs', 'compiler_config.example.json');
            fixture.data = jsondecode(fileread(configPath));
            fixture.configPath = fullfile(fixture.dir, 'compiler_config.json');
        end

        function writeJson(path, value)
            fileId = fopen(path, 'w');
            assert(fileId ~= -1, 'Cannot open temporary JSON file: %s', path);
            cleanup = onCleanup(@() fclose(fileId));
            fprintf(fileId, '%s', jsonencode(value));
        end

        function writeText(path, value)
            fileId = fopen(path, 'w');
            assert(fileId ~= -1, 'Cannot open temporary text file: %s', path);
            cleanup = onCleanup(@() fclose(fileId));
            fprintf(fileId, '%s', value);
        end

        function descriptor = getDescriptor(definition, index)
            if iscell(definition.descriptors)
                descriptor = definition.descriptors{index};
            else
                descriptor = definition.descriptors(index);
            end
        end

        function definition = setDescriptor(definition, index, descriptor)
            if iscell(definition.descriptors)
                definition.descriptors{index} = descriptor;
            else
                definition.descriptors(index) = descriptor;
            end
        end

        function verifyInvalid(testCase, fixture, expectedMessage)
            TestContractHardening.writeJson(fixture.configPath, fixture.data);
            caughtException = [];
            try
                addpath(fullfile(fileparts(fileparts(mfilename('fullpath'))), 'core'));
                load_compiler_config(fixture.configPath);
            catch caught
                caughtException = caught;
            end
            if isempty(caughtException)
                testCase.verifyTrue(false, sprintf( ...
                    'Expected InvalidConfig containing "%s".', expectedMessage));
                return;
            end
            testCase.verifyEqual(caughtException.identifier, testCase.ErrorId);
            testCase.verifyTrue(contains(caughtException.message, expectedMessage));
        end
    end
end
