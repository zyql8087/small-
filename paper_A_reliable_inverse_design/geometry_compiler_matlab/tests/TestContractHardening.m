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

        function testDescriptorDefinitionIsExplicitlyCandidate(testCase)
            path = fullfile(testCase.BaseDir, 'configs', 'descriptor_definition.json');
            definition = jsondecode(fileread(path));
            testCase.verifyEqual(char(string(definition.validation_status)), ...
                'candidate_pending_gate0');
            testCase.verifyEqual(char(string(definition.grid_convention.spacing_policy)), ...
                'isotropic_required');
            testCase.verifyEqual(definition.finite_domain_boundary_policy.void_connectivity_3d, 26);
            testCase.verifyEqual(definition.finite_domain_boundary_policy.slice_connectivity_2d, 8);
        end

        function testDeclaredContractHashesMatchFiles(testCase)
            configDir = fullfile(testCase.BaseDir, 'configs');
            config = jsondecode(fileread(fullfile(configDir, ...
                'compiler_config.example.json')));
            manifestHash = sha256_file(fullfile(configDir, ...
                'parameter_domain_manifest.json'), testCase.ErrorId, ...
                'parameter-domain manifest');
            descriptorHash = sha256_file(fullfile(configDir, ...
                'descriptor_definition.json'), testCase.ErrorId, ...
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
            path = fullfile(fixture.dir, 'descriptor_definition.json');
            definition = jsondecode(fileread(path));
            if iscell(definition.descriptors)
                definition.descriptors{5}.algorithm_params.slice_count = 25;
            else
                definition.descriptors(5).algorithm_params.slice_count = 25;
            end
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
    end

    methods (Static, Access = private)
        function fixture = createFixture(baseDir)
            fixture.dir = tempname;
            mkdir(fixture.dir);
            fixture.cleanup = onCleanup(@() rmdir(fixture.dir, 's'));
            copyfile(fullfile(baseDir, 'configs', 'descriptor_definition.json'), ...
                fullfile(fixture.dir, 'descriptor_definition.json'));
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
