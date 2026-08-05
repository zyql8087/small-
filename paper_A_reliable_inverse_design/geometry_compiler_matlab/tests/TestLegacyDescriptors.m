classdef TestLegacyDescriptors < matlab.unittest.TestCase
%TESTLEGACYDESCRIPTORS Tests TPMS-Designer-compatible legacy descriptors.

    properties (Access = private)
        BaseDir
    end

    methods (TestClassSetup)
        function setupClass(testCase)
            testCase.BaseDir = fileparts(fileparts(mfilename('fullpath')));
            addpath(fullfile(testCase.BaseDir, 'core'));
            addpath(fullfile(testCase.BaseDir, 'configs'));
        end
    end

    methods (Test)
        function testArrayOperationsUseLegacyNormalizations(testCase)
            solid = false(4, 4, 4);
            solid(1:3, 1:3, 1:3) = true;
            field = TestLegacyDescriptors.makeField(solid, 1, 12, ...
                struct('x', [0, 3], 'y', [0, 3], 'z', [0, 3]));

            result = compute_legacy_small_descriptors(field, repmat('a', 1, 64));

            testCase.verifyEqual(result.profile, 'legacy_small');
            testCase.verifyEqual(result.values.relativeVolume, 1, 'AbsTol', 0);
            testCase.verifyEqual(result.values.relativeArea, 12 / 54, ...
                'AbsTol', 1e-15);
            testCase.verifyEqual(result.values.areaMean, 27 / 4, 'AbsTol', 0);
            testCase.verifyTrue(isfinite(result.values.thickness));
            testCase.verifyTrue(isfinite(result.values.poreDiameter));
        end

        function testPeriodicDiametersMatchExplicitThreeTileReference(testCase)
            masks = TestLegacyDescriptors.periodicAxisFixtures();
            for index = 1:numel(masks)
                field = TestLegacyDescriptors.makeField(masks{index}, 0.25, ...
                    1, struct('x', [0, 1], 'y', [0, 1], 'z', [0, 1]));
                result = compute_legacy_small_descriptors(field, ...
                    repmat('b', 1, 64));
                [expectedThickness, expectedPore] = ...
                    TestLegacyDescriptors.explicitPeriodicDiameters( ...
                    masks{index}, field.voxel_size_mm);
                testCase.verifyEqual(result.values.thickness, ...
                    expectedThickness, 'AbsTol', 0);
                testCase.verifyEqual(result.values.poreDiameter, ...
                    expectedPore, 'AbsTol', 0);
            end
        end

        function testRejectsNonintegralLegacyEndpointGrid(testCase)
            config = load_compiler_config(fullfile(testCase.BaseDir, ...
                'configs', 'compiler_config.example.json'));
            config.geometry_parameters.domain_over_l.z = [0, 2.1];
            raw = struct('c0', 0.1, 'c1', 0.1, 'c2', 0.1, 'w', 0);
            projected = project_method_constraints('M1', raw, config);

            testCase.verifyError(@() build_legacy_descriptor_field( ...
                projected, config, 31, 1), ...
                'MATLABGyroid:DescriptorProfileInvalid');
        end

        function testRejectsLegacyDomainWithoutAllAxes(testCase)
            config = load_compiler_config(fullfile(testCase.BaseDir, ...
                'configs', 'compiler_config.example.json'));
            config.geometry_parameters.domain_over_l = ...
                rmfield(config.geometry_parameters.domain_over_l, 'z');
            raw = struct('c0', 0.1, 'c1', 0.1, 'c2', 0.1, 'w', 0);
            projected = project_method_constraints('M1', raw, config);

            testCase.verifyError(@() build_legacy_descriptor_field( ...
                projected, config, 24, 1), ...
                'MATLABGyroid:DescriptorProfileInvalid');
        end

        function testBuildsM1EndpointGridAndPhysicalSurfaceArea(testCase)
            config = load_compiler_config(fullfile(testCase.BaseDir, ...
                'configs', 'compiler_config.example.json'));
            raw = struct('c0', 0.1, 'c1', 0.1, 'c2', 0.1, 'w', 0);
            projected = project_method_constraints('M1', raw, config);

            field = build_legacy_descriptor_field(projected, config, 24, 1);

            testCase.verifySize(field.solid, [25, 25, 49]);
            testCase.verifyEqual(field.voxel_size_mm, 1 / 24, 'AbsTol', 0);
            testCase.verifyGreaterThan(field.surface_area_mm2, 0);
            testCase.verifyGreaterThan(field.triangle_count, 0);
            testCase.verifyEqual(field.bounds_mm.z, [0, 2], 'AbsTol', 0);
        end

        function testResultValidatorRejectsMissingDescriptor(testCase)
            result = struct('profile', 'legacy_small', ...
                'definition_sha256', repmat('c', 1, 64), ...
                'sampling', struct(), 'units', struct(), ...
                'values', struct('relativeVolume', 0.2), ...
                'diagnostics', struct());

            testCase.verifyError(@() validate_descriptor_result(result, ...
                'legacy_small', repmat('c', 1, 64)), ...
                'MATLABGyroid:DescriptorProfileInvalid');
        end

        function testLegacyFieldWithoutTriangleCountIsRejected(testCase)
            field = TestLegacyDescriptors.makeField(true(3, 3, 3), 0.5, ...
                1, struct('x', [0, 1], 'y', [0, 1], 'z', [0, 1]));
            field.solid(2, 2, 2) = false;
            field = rmfield(field, 'triangle_count');

            testCase.verifyError(@() compute_legacy_small_descriptors( ...
                field, repmat('d', 1, 64)), ...
                'MATLABGyroid:DescriptorProfileInvalid');
        end

        function testResultValidatorRejectsMalformedDefinitionHash(testCase)
            result = struct('profile', 'legacy_small', ...
                'definition_sha256', 'not-a-sha256', ...
                'sampling', struct(), ...
                'units', struct('relativeVolume', 'dimensionless', ...
                'relativeArea', 'dimensionless', 'thickness', 'mm', ...
                'poreDiameter', 'mm', 'areaMean', 'mm2'), ...
                'values', struct('relativeVolume', 0.2, ...
                'relativeArea', 0.3, 'thickness', 0.4, ...
                'poreDiameter', 0.5, 'areaMean', 0.6), ...
                'diagnostics', struct());

            testCase.verifyError(@() validate_descriptor_result(result, ...
                'legacy_small', 'not-a-sha256'), ...
                'MATLABGyroid:DescriptorProfileInvalid');
        end
    end

    methods (Static, Access = private)
        function field = makeField(solid, voxelSizeMm, surfaceAreaMm2, boundsMm)
            field = struct('solid', solid, 'voxel_size_mm', voxelSizeMm, ...
                'surface_area_mm2', surfaceAreaMm2, 'bounds_mm', boundsMm, ...
                'samples_per_reference_length', 4, ...
                'reference_length_mm', 1, 'triangle_count', 12);
        end

        function masks = periodicAxisFixtures()
            masks = cell(1, 3);
            masks{1} = false(5, 5, 5);
            masks{1}([1, 5], :, :) = true;
            masks{2} = false(5, 5, 5);
            masks{2}(:, [1, 5], :) = true;
            masks{3} = false(5, 5, 5);
            masks{3}(:, :, [1, 5]) = true;
        end

        function [thickness, poreDiameter] = explicitPeriodicDiameters( ...
                solid, voxelSizeMm)
            tiled = repmat(solid, 3, 3, 3);
            solidBarrier = padarray(~tiled, [1, 1, 1], true, 'both');
            voidBarrier = padarray(tiled, [1, 1, 1], true, 'both');
            thickness = 2 * voxelSizeMm * max(bwdist(solidBarrier), [], 'all');
            poreDiameter = 2 * voxelSizeMm * max(bwdist(voidBarrier), [], 'all');
        end
    end
end
