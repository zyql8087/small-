classdef TestPhysicalDescriptors < matlab.unittest.TestCase
%TESTPHYSICALDESCRIPTORS Tests finite-specimen physical M04 descriptors.

    properties (Access = private)
        BaseDir
    end

    methods (TestClassSetup)
        function setupClass(testCase)
            testCase.BaseDir = fileparts(fileparts(mfilename('fullpath')));
            addpath(fullfile(testCase.BaseDir, 'core'));
        end
    end

    methods (Test)
        function testPhysicalScaleLaws(testCase)
            solid = true(21, 21, 21);
            solid(7:15, 7:15, :) = false;
            definitionHash = repmat('b', 1, 64);
            meshOne = TestPhysicalDescriptors.boxMesh([0, 1], [0, 1], [0, 1]);
            resultOne = compute_physical_m04_descriptors(solid, 1 / 21, ...
                meshOne, [0, 1; 0, 1; 0, 1], definitionHash);

            meshThree = meshOne;
            meshThree.vertices = 3 .* meshThree.vertices;
            resultThree = compute_physical_m04_descriptors(solid, 3 / 21, ...
                meshThree, [0, 3; 0, 3; 0, 3], definitionHash);

            testCase.verifyEqual(resultThree.values.relativeVolume, ...
                resultOne.values.relativeVolume, 'AbsTol', 0);
            testCase.verifyEqual(resultThree.values.relativeArea, ...
                resultOne.values.relativeArea / 3, 'RelTol', 1e-12);
            testCase.verifyEqual(resultThree.values.thickness, ...
                3 * resultOne.values.thickness, 'RelTol', 1e-12);
            testCase.verifyEqual(resultThree.values.poreDiameter, ...
                3 * resultOne.values.poreDiameter, 'RelTol', 1e-12);
            testCase.verifyEqual(resultThree.values.areaMean, ...
                9 * resultOne.values.areaMean, 'RelTol', 1e-12);
            testCase.verifyEqual(resultOne.units.relativeArea, 'mm^-1');
        end

        function testSelectsLargestFiniteVoidComponent(testCase)
            solid = true(7, 7, 7);
            solid(2:3, 2:3, 2:3) = false;
            solid(6, 6, 6) = false;
            mesh = TestPhysicalDescriptors.boxMesh([0, 7], [0, 7], [0, 7]);

            result = compute_physical_m04_descriptors(solid, 1, mesh, ...
                [0, 7; 0, 7; 0, 7], repmat('c', 1, 64));

            testCase.verifyEqual(result.diagnostics.void_component_count, 2);
            testCase.verifyEqual(result.diagnostics.selected_void_component_size, 8);
            testCase.verifyEqual(result.diagnostics.largest_void_component_size, 8);
            testCase.verifyGreaterThan(result.values.poreDiameter, 0);
            testCase.verifyEqual(result.profile, 'physical_m04');
        end

        function testUsesTwentySixEndpointInclusiveSliceIndices(testCase)
            solid = true(5, 5, 4);
            solid(2:4, 2:4, [1, 4]) = false;
            mesh = TestPhysicalDescriptors.boxMesh([0, 5], [0, 5], [0, 4]);

            result = compute_physical_m04_descriptors(solid, 1, mesh, ...
                [0, 5; 0, 5; 0, 4], repmat('d', 1, 64));

            expectedIndices = round(linspace(1, 4, 26));
            testCase.verifyEqual(result.diagnostics.slice_indices, expectedIndices);
            testCase.verifyEqual(result.diagnostics.nonempty_slice_count, ...
                sum(ismember(expectedIndices, [1, 4])));
            testCase.verifyEqual(result.values.areaMean, 9, 'AbsTol', 0);
        end

        function testRejectsAllSolidAndAllVoidMasks(testCase)
            mesh = TestPhysicalDescriptors.boxMesh([0, 3], [0, 3], [0, 3]);
            hash = repmat('e', 1, 64);
            testCase.verifyError(@() compute_physical_m04_descriptors( ...
                true(3, 3, 3), 1, mesh, [0, 3; 0, 3; 0, 3], hash), ...
                'MATLABGyroid:DescriptorProfileInvalid');
            testCase.verifyError(@() compute_physical_m04_descriptors( ...
                false(3, 3, 3), 1, mesh, [0, 3; 0, 3; 0, 3], hash), ...
                'MATLABGyroid:DescriptorProfileInvalid');
        end

        function testRejectsOpenSurfaceMesh(testCase)
            solid = true(5, 5, 5);
            solid(3, 3, 3) = false;
            mesh = TestPhysicalDescriptors.boxMesh([0, 5], [0, 5], [0, 5]);
            mesh.faces = mesh.faces(1, :);

            testCase.verifyError(@() compute_physical_m04_descriptors( ...
                solid, 1, mesh, [0, 5; 0, 5; 0, 5], ...
                repmat('f', 1, 64)), ...
                'MATLABGyroid:DescriptorProfileInvalid');
        end

        function testRejectsLogicalMeshVertices(testCase)
            solid = true(5, 5, 5);
            solid(3, 3, 3) = false;
            mesh = TestPhysicalDescriptors.boxMesh([0, 5], [0, 5], [0, 5]);
            mesh.vertices = logical(mesh.vertices);

            testCase.verifyError(@() compute_physical_m04_descriptors( ...
                solid, 1, mesh, [0, 5; 0, 5; 0, 5], ...
                repmat('a', 1, 64)), ...
                'MATLABGyroid:DescriptorProfileInvalid');
        end

        function testRejectsInconsistentBoundsAndInvalidHash(testCase)
            solid = true(5, 5, 5);
            solid(3, 3, 3) = false;
            stretchedMesh = TestPhysicalDescriptors.boxMesh( ...
                [0, 5], [0, 5], [0, 10]);
            validMesh = TestPhysicalDescriptors.boxMesh([0, 5], [0, 5], [0, 5]);

            testCase.verifyError(@() compute_physical_m04_descriptors( ...
                solid, 1, stretchedMesh, [0, 5; 0, 5; 0, 10], ...
                repmat('a', 1, 64)), ...
                'MATLABGyroid:DescriptorProfileInvalid');
            testCase.verifyError(@() compute_physical_m04_descriptors( ...
                solid, 1, validMesh, [0, 5; 0, 5; 0, 5], ...
                repmat('A', 1, 64)), ...
                'MATLABGyroid:DescriptorProfileInvalid');
        end
    end

    methods (Static, Access = private)
        function mesh = boxMesh(xBounds, yBounds, zBounds)
            vertices = [ ...
                xBounds(1), yBounds(1), zBounds(1); ...
                xBounds(2), yBounds(1), zBounds(1); ...
                xBounds(2), yBounds(2), zBounds(1); ...
                xBounds(1), yBounds(2), zBounds(1); ...
                xBounds(1), yBounds(1), zBounds(2); ...
                xBounds(2), yBounds(1), zBounds(2); ...
                xBounds(2), yBounds(2), zBounds(2); ...
                xBounds(1), yBounds(2), zBounds(2)];
            faces = [ ...
                1, 3, 2; 1, 4, 3; 5, 6, 7; 5, 7, 8; ...
                1, 2, 6; 1, 6, 5; 2, 3, 7; 2, 7, 6; ...
                3, 4, 8; 3, 8, 7; 4, 1, 5; 4, 5, 8];
            mesh = struct('vertices', vertices, 'faces', faces);
        end
    end
end
